from airflow.decorators import dag, task
from datetime import datetime, timedelta
import urllib.request
import requests
import xml.etree.ElementTree as ET
import os

default_args = {
    'owner': 'admin',
    'depends_on_past': False,
    'start_date': datetime(2026, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

@dag(
    default_args=default_args,
    schedule_interval='@daily',
    catchup=False,
    tags=['rag', 'etl', 'ingestion'],
    description='An ETL pipeline to Extract arXiv metadata, Download PDFs, and Load into the Vector Database.'
)
def daily_arxiv_etl_pipeline():
    
    @task()
    def extract_arxiv_metadata() -> list:
        """
        EXTRACT: Fetch the latest AI paper metadata from the arXiv API.
        """
        print("Extracting metadata for the latest AI papers...")
        url = "http://export.arxiv.org/api/query?search_query=cat:cs.AI&sortBy=lastUpdatedDate&sortOrder=descending&max_results=2"
        
        response = requests.get(url)
        root = ET.fromstring(response.text)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        
        papers = []
        for entry in root.findall('atom:entry', ns):
            title = entry.find('atom:title', ns).text.replace('\n', ' ')
            pdf_url = None
            for link in entry.findall('atom:link', ns):
                if link.attrib.get('title') == 'pdf':
                    pdf_url = link.attrib['href']
                    break
            
            if pdf_url:
                papers.append({"title": title, "pdf_url": pdf_url})
                
        print(f"Extracted {len(papers)} papers.")
        return papers

    @task()
    def download_papers(papers: list) -> list:
        """
        TRANSFORM/DOWNLOAD: Download the PDFs to local temporary storage.
        """
        downloaded_files = []
        for i, paper in enumerate(papers):
            title = paper['title']
            pdf_url = paper['pdf_url']
            print(f"Downloading: {title} ({pdf_url})")
            
            pdf_path = f"/tmp/arxiv_paper_{i}.pdf"
            urllib.request.urlretrieve(pdf_url, pdf_path)
            downloaded_files.append(pdf_path)
            
        return downloaded_files

    @task()
    def load_to_vector_db(file_paths: list):
        """
        LOAD: Push the downloaded PDFs to the FastAPI ingestion endpoint (which handles chunking and vector storage).
        """
        api_url = "http://api:8000/api/v1/ingest/"
        
        for pdf_path in file_paths:
            print(f"Loading {pdf_path} to Vector DB via API...")
            
            if not os.path.exists(pdf_path):
                print(f"File not found: {pdf_path}")
                continue
                
            with open(pdf_path, 'rb') as f:
                files = {'file': ('paper.pdf', f, 'application/pdf')}
                try:
                    res = requests.post(api_url, files=files, timeout=120)
                    print(f"Load result: {res.status_code} - {res.text}")
                except Exception as e:
                    print(f"Failed to load: {e}")
            
            # Clean up temporary file
            os.remove(pdf_path)
            print(f"Cleaned up {pdf_path}")

    # Define the DAG dependency chain
    metadata = extract_arxiv_metadata()
    downloaded_pdfs = download_papers(metadata)
    load_to_vector_db(downloaded_pdfs)

# Instantiate the DAG
etl_dag = daily_arxiv_etl_pipeline()
