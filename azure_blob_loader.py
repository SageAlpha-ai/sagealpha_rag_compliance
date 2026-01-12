"""
Azure Blob Storage Document Loader - AUDIT-GRADE VERSION

ROW-LEVEL financial ingestion with:
- Explicit fiscal year binding (FY2012)
- Revenue + Net Income bound to same row
- Handles TRANSPOSED financial reports (metrics as rows, years as columns)
"""

import os
import io
import re
from typing import List, Dict, Optional, Tuple

from azure.storage.blob import BlobServiceClient, ContainerClient
from pypdf import PdfReader
import pandas as pd


def get_container_client() -> ContainerClient:
    """Creates Azure Blob Storage container client."""
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    container_name = os.getenv("AZURE_BLOB_CONTAINER_NAME")
    
    if not connection_string:
        raise ValueError("AZURE_STORAGE_CONNECTION_STRING not set")
    if not container_name:
        raise ValueError("AZURE_BLOB_CONTAINER_NAME not set")
    
    client = BlobServiceClient.from_connection_string(connection_string)
    return client.get_container_client(container_name)


def download_blob(container_client: ContainerClient, blob_name: str) -> bytes:
    """Downloads blob to memory."""
    return container_client.get_blob_client(blob_name).download_blob().readall()


def normalize_fiscal_year(value) -> Optional[str]:
    """
    Normalizes fiscal year to FYxxxx format.
    
    Examples:
    - 2012-03 -> FY2012
    - 2011-12 -> FY2012 (fiscal year ending in 2012)
    - Mar-2012 -> FY2012
    """
    if pd.isna(value):
        return None
    
    value_str = str(value).strip()
    
    # Match pattern like "2012-03" (fiscal year ending March 2012)
    fy_match = re.match(r'(\d{4})-(\d{2})', value_str)
    if fy_match:
        year = fy_match.group(1)
        return f"FY{year}"
    
    # Match 4-digit year
    year_match = re.search(r'(19|20)\d{2}', value_str)
    if year_match:
        year = year_match.group(0)
        return f"FY{year}"
    
    return None


def parse_excel_transposed(content: bytes, blob_name: str) -> List[Dict]:
    """
    Parses TRANSPOSED financial Excel where:
    - Metrics are in rows (column 0)
    - Fiscal years are in columns (row containing fiscal periods)
    
    Creates one chunk per fiscal year with all available metrics.
    """
    documents = []
    excel_file = io.BytesIO(content)
    
    try:
        df = pd.read_excel(excel_file, header=None)
        
        print(f"    Shape: {df.shape}")
        
        # Find the fiscal period row (contains year patterns like "2012-03")
        fiscal_row_idx = None
        fiscal_years = {}  # {col_idx: "FY2012"}
        
        for idx, row in df.iterrows():
            year_cols = []
            for col in range(1, min(len(row), 25)):
                val = row[col]
                if pd.notna(val) and re.match(r'\d{4}-\d{2}', str(val)):
                    year_cols.append(col)
            
            if len(year_cols) >= 5:  # Found the fiscal period row
                fiscal_row_idx = idx
                for col in range(1, len(row)):
                    fy = normalize_fiscal_year(row[col])
                    if fy:
                        fiscal_years[col] = fy
                print(f"    Found fiscal periods at row {idx}: {list(fiscal_years.values())[:5]}...")
                break
        
        if not fiscal_years:
            print("    [WARN] Could not find fiscal period row")
            # Fallback to general parsing
            return parse_excel_fallback(df, blob_name)
        
        # Find key financial metrics rows
        metrics = {}  # {metric_name: {col_idx: value}}
        
        key_metrics = {
            'revenue': ['revenue'],
            'net_income': ['net income'],
            'ebitda': ['ebitda'],
            'gross_profit': ['gross profit'],
            'operating_income': ['operating income', 'ebit'],
            'total_assets': ['total assets'],
            'total_equity': ['total equity', "total stockholders' equity"],
            'eps': ['earnings per share (diluted)', 'eps (diluted)'],
        }
        
        for idx, row in df.iterrows():
            if idx <= fiscal_row_idx:
                continue
                
            metric_name = str(row[0]).strip().lower() if pd.notna(row[0]) else ""
            
            for key, patterns in key_metrics.items():
                # Exact match for cleaner results
                if metric_name in patterns or any(metric_name == p for p in patterns):
                    metrics[key] = {}
                    for col, fy in fiscal_years.items():
                        val = row[col]
                        if pd.notna(val) and str(val) != '-':
                            try:
                                metrics[key][fy] = float(val)
                            except:
                                pass
                    print(f"    Found {key}: Row {idx} ({metric_name})")
                    break
        
        # Create one document per fiscal year with all metrics
        for col, fiscal_year in fiscal_years.items():
            if fiscal_year == "FYNAN" or "TTM" in str(fiscal_year):
                continue
            
            # Gather all metrics for this year
            revenue = metrics.get('revenue', {}).get(fiscal_year)
            net_income = metrics.get('net_income', {}).get(fiscal_year)
            ebitda = metrics.get('ebitda', {}).get(fiscal_year)
            gross_profit = metrics.get('gross_profit', {}).get(fiscal_year)
            operating_income = metrics.get('operating_income', {}).get(fiscal_year)
            total_assets = metrics.get('total_assets', {}).get(fiscal_year)
            total_equity = metrics.get('total_equity', {}).get(fiscal_year)
            eps = metrics.get('eps', {}).get(fiscal_year)
            
            # Only create if we have at least revenue or net income
            if revenue is None and net_income is None:
                continue
            
            # Build structured text
            text_lines = [
                "Entity: Oracle Financial Services Software Ltd",
                "Statement: Income Statement / Financial Summary",
                f"Fiscal Year: {fiscal_year}",
                "Currency: INR",
                "Unit: millions (except per share data)",
                "",
            ]
            
            if revenue is not None:
                text_lines.append(f"Revenue: INR {revenue:,.2f} million")
            
            if net_income is not None:
                text_lines.append(f"Net Income: INR {net_income:,.2f} million")
            
            if ebitda is not None:
                text_lines.append(f"EBITDA: INR {ebitda:,.2f} million")
            
            if gross_profit is not None:
                text_lines.append(f"Gross Profit: INR {gross_profit:,.2f} million")
            
            if operating_income is not None:
                text_lines.append(f"Operating Income: INR {operating_income:,.2f} million")
            
            if total_assets is not None:
                text_lines.append(f"Total Assets: INR {total_assets:,.2f} million")
            
            if total_equity is not None:
                text_lines.append(f"Total Equity: INR {total_equity:,.2f} million")
            
            if eps is not None:
                text_lines.append(f"EPS (Diluted): INR {eps:,.2f}")
            
            text_lines.extend([
                "",
                f"Source: {blob_name}"
            ])
            
            structured_text = "\n".join(text_lines)
            
            # Debug print
            print(f"    Ingested financial row -> {fiscal_year} | Revenue={revenue} | NetIncome={net_income}")
            
            documents.append({
                "text": structured_text,
                "metadata": {
                    "company": "Oracle Financial Services Software Ltd",
                    "statement": "Income Statement",
                    "fiscal_year": fiscal_year,
                    "currency": "INR",
                    "unit": "millions",
                    "revenue": revenue,
                    "net_income": net_income,
                    "ebitda": ebitda,
                    "source": f"azure_blob/{blob_name}",
                    "document_type": "financial_row"
                }
            })
        
        # Also add quarterly data if present (look for "Quarterly Data:" section)
        quarterly_section = False
        quarterly_fiscal_years = {}
        quarterly_metrics = {}
        
        for idx, row in df.iterrows():
            first_cell = str(row[0]).strip() if pd.notna(row[0]) else ""
            
            if 'quarterly data' in first_cell.lower():
                quarterly_section = True
                continue
            
            if quarterly_section:
                # Check if this is a fiscal period row for quarterly
                year_count = 0
                for col in range(1, min(len(row), 25)):
                    val = row[col]
                    if pd.notna(val) and re.match(r'\d{4}Q\d', str(val)):
                        year_count += 1
                        quarterly_fiscal_years[col] = str(val)
                
                if year_count >= 3:
                    continue
                
                # Look for metrics
                metric_name = first_cell.lower()
                if metric_name == 'revenue':
                    quarterly_metrics['revenue'] = {}
                    for col, qfy in quarterly_fiscal_years.items():
                        val = row[col]
                        if pd.notna(val) and str(val) != '-':
                            try:
                                quarterly_metrics['revenue'][qfy] = float(val)
                            except:
                                pass
                
                if metric_name == 'net income':
                    quarterly_metrics['net_income'] = {}
                    for col, qfy in quarterly_fiscal_years.items():
                        val = row[col]
                        if pd.notna(val) and str(val) != '-':
                            try:
                                quarterly_metrics['net_income'][qfy] = float(val)
                            except:
                                pass
        
        # Create quarterly documents
        for qfy in quarterly_fiscal_years.values():
            revenue = quarterly_metrics.get('revenue', {}).get(qfy)
            net_income = quarterly_metrics.get('net_income', {}).get(qfy)
            
            if revenue is None and net_income is None:
                continue
            
            text_lines = [
                "Entity: Oracle Financial Services Software Ltd",
                "Statement: Quarterly Income Statement",
                f"Quarter: {qfy}",
                "Currency: INR",
                "Unit: millions",
                "",
            ]
            
            if revenue is not None:
                text_lines.append(f"Revenue: INR {revenue:,.2f} million")
            if net_income is not None:
                text_lines.append(f"Net Income: INR {net_income:,.2f} million")
            
            text_lines.append(f"\nSource: {blob_name}")
            
            documents.append({
                "text": "\n".join(text_lines),
                "metadata": {
                    "company": "Oracle Financial Services Software Ltd",
                    "statement": "Quarterly Income Statement",
                    "quarter": qfy,
                    "currency": "INR",
                    "unit": "millions",
                    "revenue": revenue,
                    "net_income": net_income,
                    "source": f"azure_blob/{blob_name}",
                    "document_type": "quarterly_financial"
                }
            })
        
    except Exception as e:
        print(f"    [ERROR] Failed to parse Excel: {e}")
        import traceback
        traceback.print_exc()
    
    return documents


def parse_excel_fallback(df: pd.DataFrame, blob_name: str) -> List[Dict]:
    """Fallback parser for non-standard Excel files."""
    documents = []
    
    # Create chunks from rows
    for idx, row in df.iterrows():
        row_text = " | ".join([str(v) for v in row.values if pd.notna(v)])
        if len(row_text.strip()) > 30:
            documents.append({
                "text": f"Oracle Financial Services - Data Row\n{row_text}\nSource: {blob_name}",
                "metadata": {
                    "company": "Oracle Financial Services Software Ltd",
                    "currency": "INR",
                    "unit": "millions",
                    "source": f"azure_blob/{blob_name}",
                    "row_index": idx,
                    "document_type": "financial_data"
                }
            })
    
    return documents


def parse_pdf_with_context(content: bytes, blob_name: str) -> List[Dict]:
    """Parses PDF with financial context preservation."""
    documents = []
    pdf_file = io.BytesIO(content)
    
    try:
        reader = PdfReader(pdf_file)
        
        for page_num, page in enumerate(reader.pages, 1):
            page_text = page.extract_text()
            if not page_text or len(page_text.strip()) < 50:
                continue
            
            # Extract fiscal year if present
            fiscal_year = normalize_fiscal_year(page_text[:500])
            
            # Add context header
            structured_text = f"""Financial Report - Oracle Financial Services Software Ltd
Currency: INR
Unit: millions
Page: {page_num}
{f'Fiscal Year: {fiscal_year}' if fiscal_year else ''}

{page_text}"""
            
            documents.append({
                "text": structured_text,
                "metadata": {
                    "company": "Oracle Financial Services Software Ltd",
                    "currency": "INR",
                    "unit": "millions",
                    "page": page_num,
                    "fiscal_year": fiscal_year or "Unknown",
                    "source": f"azure_blob/{blob_name}",
                    "document_type": "financial_report"
                }
            })
            
    except Exception as e:
        print(f"    [ERROR] Failed to parse PDF: {e}")
    
    return documents


def load_azure_documents() -> List[Dict]:
    """
    Loads PDF and Excel from Azure Blob Storage with ROW-LEVEL extraction.
    """
    if not os.getenv("AZURE_STORAGE_CONNECTION_STRING"):
        print("Azure Blob Storage not configured. Skipping.")
        return []
    
    try:
        container_client = get_container_client()
    except Exception as e:
        print(f"Failed to connect to Azure: {e}")
        return []
    
    documents = []
    
    try:
        for blob in container_client.list_blobs():
            blob_name = blob.name
            
            if not blob_name.lower().endswith(('.pdf', '.xlsx', '.xls')):
                continue
            
            print(f"  Loading: {blob_name}")
            
            try:
                content = download_blob(container_client, blob_name)
                
                if blob_name.lower().endswith('.pdf'):
                    docs = parse_pdf_with_context(content, blob_name)
                elif blob_name.lower().endswith(('.xlsx', '.xls')):
                    docs = parse_excel_transposed(content, blob_name)
                else:
                    continue
                
                documents.extend(docs)
                print(f"    [OK] Extracted {len(docs)} chunks")
                
            except Exception as e:
                print(f"    [ERROR] {e}")
                
    except Exception as e:
        print(f"Failed to list blobs: {e}")
    
    # Count financial rows
    financial_rows = sum(1 for d in documents if d.get('metadata', {}).get('document_type') == 'financial_row')
    print(f"\nTotal: {len(documents)} chunks ({financial_rows} explicit financial rows)")
    
    return documents
