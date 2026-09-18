"""
=============================================================================
STAGE 1 (Expanded): Azure AI Document Intelligence - Full Context & Tables
=============================================================================
"""

import os
import time
import pandas as pd
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeResult

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
ENDPOINT = ""
KEY = ""
INPUT_DOCUMENT = "C:/Users/HP/Desktop/OCR-Benchmark/test/Article.pdf"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

OUTPUT_MARKDOWN = os.path.join(SCRIPT_DIR, "azure_full_document_context.md")
OUTPUT_EXCEL = os.path.join(SCRIPT_DIR, "azure_extracted_tables.xlsx")

def analyze_full_context_and_tables(doc_path: str, md_out: str, excel_out: str):
    if not os.path.exists(doc_path):
        print(f"Error: '{doc_path}' not found.")
        return

    client = DocumentIntelligenceClient(
        endpoint=ENDPOINT, 
        credential=AzureKeyCredential(KEY)
    )

    print(f"[*] Sending '{doc_path}' to Azure AI Document Intelligence...")
    start_time = time.time()

    with open(doc_path, "rb") as f:
        # We pass output_content_format="markdown" to extract full page context
        poller = client.begin_analyze_document(
            model_id="prebuilt-layout", 
            body=f,
            output_content_format="markdown"
        )
        result: AnalyzeResult = poller.result()

    execution_time = time.time() - start_time
    print(f"[+] Processing completed in {execution_time:.2f} seconds.")

    # -----------------------------------------------------------------------
    # 1. EXPORT FULL CONTEXT (Paragraphs + Tables + Headings) AS MARKDOWN
    # -----------------------------------------------------------------------
    full_content = result.content if result.content else "No content extracted."
    
    with open(md_out, "w", encoding="utf-8") as f:
        f.write(f"<!-- Processing Time: {execution_time:.2f} seconds -->\n\n")
        f.write(full_content)

    print(f"[SUCCESS] Full document context saved to: {md_out}")

    # -----------------------------------------------------------------------
    # 2. EXPORT EXPLICIT TABULAR DATA TO EXCEL
    # -----------------------------------------------------------------------
    tables = result.tables if result.tables else []
    print(f"[+] Total Tables Found: {len(tables)}")

    if tables:
        with pd.ExcelWriter(excel_out, engine="openpyxl") as writer:
            for idx, table in enumerate(tables):
                sheet_name = f"Table_{idx + 1}"
                
                # Reconstruct 2D matrix for Excel
                matrix = [["" for _ in range(table.column_count)] for _ in range(table.row_count)]
                for cell in table.cells:
                    matrix[cell.row_index][cell.column_index] = cell.content.replace("\n", " ").strip()

                df = pd.DataFrame(matrix[1:], columns=matrix[0]) if len(matrix) > 1 else pd.DataFrame(matrix)
                df.to_excel(writer, sheet_name=sheet_name, index=False)

        print(f"[SUCCESS] Extracted tables saved to: {excel_out}")
    else:
        print("[-] No standalone tables found to export to Excel.")

if __name__ == "__main__":
    analyze_full_context_and_tables(INPUT_DOCUMENT, OUTPUT_MARKDOWN, OUTPUT_EXCEL)