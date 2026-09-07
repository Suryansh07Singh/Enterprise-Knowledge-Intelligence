import os
import io
import re
from typing import List, Dict, Any
from pypdf import PdfReader
import docx
from bs4 import BeautifulSoup
import markdown

class DocumentParser:
    """Multi-format parser supporting PDF, DOCX, Markdown, TXT, and HTML.
    Extracts text while preserving page numbers and section headers where possible.
    """
    
    @staticmethod
    def parse_file(file_path: str, file_type: str) -> List[Dict[str, Any]]:
        """Parses a file and returns a list of pages/sections with structure:
        [{"page_number": int, "section_title": str, "text": str}]
        """
        ext = file_type.lower().strip(".")
        if ext == "pdf":
            return DocumentParser._parse_pdf(file_path)
        elif ext in ["docx", "doc"]:
            return DocumentParser._parse_docx(file_path)
        elif ext in ["md", "markdown"]:
            return DocumentParser._parse_markdown(file_path)
        elif ext in ["html", "htm"]:
            return DocumentParser._parse_html(file_path)
        else: # txt or default
            return DocumentParser._parse_txt(file_path)

    @staticmethod
    def _parse_pdf(file_path: str) -> List[Dict[str, Any]]:
        reader = PdfReader(file_path)
        extracted = []
        current_section = "Introduction"
        
        for idx, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            text = DocumentParser._clean_text(text)
            if not text:
                continue
                
            # Attempt simple heading heuristic
            lines = text.split("\n")
            for line in lines[:3]:
                line_str = line.strip()
                if len(line_str) > 3 and len(line_str) < 80 and (line_str.isupper() or line_str.istitle() or line_str.startswith("#")):
                    current_section = re.sub(r'^[#\s\d\.]+', '', line_str).strip() or current_section
                    break
                    
            extracted.append({
                "page_number": idx,
                "section_title": current_section,
                "text": text
            })
        return extracted if extracted else [{"page_number": 1, "section_title": "General", "text": ""}]

    @staticmethod
    def _parse_docx(file_path: str) -> List[Dict[str, Any]]:
        doc = docx.Document(file_path)
        extracted = []
        current_section = "General"
        current_text = []
        page_num = 1

        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue
            if para.style.name.startswith("Heading") or text.isupper():
                if current_text:
                    extracted.append({
                        "page_number": page_num,
                        "section_title": current_section,
                        "text": DocumentParser._clean_text("\n".join(current_text))
                    })
                    current_text = []
                current_section = text
            else:
                current_text.append(text)

        if current_text:
            extracted.append({
                "page_number": page_num,
                "section_title": current_section,
                "text": DocumentParser._clean_text("\n".join(current_text))
            })

        return extracted if extracted else [{"page_number": 1, "section_title": "General", "text": ""}]

    @staticmethod
    def _parse_markdown(file_path: str) -> List[Dict[str, Any]]:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        sections = re.split(r'\n(?=#+\s+)', content)
        extracted = []
        
        for idx, sec in enumerate(sections, start=1):
            sec_str = sec.strip()
            if not sec_str:
                continue
            match = re.match(r'^(#+)\s+(.+)', sec_str)
            if match:
                title = match.group(2).strip()
            else:
                title = f"Section {idx}"
            
            extracted.append({
                "page_number": 1,
                "section_title": title,
                "text": DocumentParser._clean_text(sec_str)
            })
            
        return extracted if extracted else [{"page_number": 1, "section_title": "General", "text": content}]

    @staticmethod
    def _parse_html(file_path: str) -> List[Dict[str, Any]]:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            soup = BeautifulSoup(f.read(), "html.parser")

        # Strip scripts and styles
        for script in soup(["script", "style"]):
            script.extract()

        text = soup.get_text(separator="\n")
        cleaned = DocumentParser._clean_text(text)
        return [{"page_number": 1, "section_title": soup.title.string if soup.title else "Web Page", "text": cleaned}]

    @staticmethod
    def _parse_txt(file_path: str) -> List[Dict[str, Any]]:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        return [{"page_number": 1, "section_title": "Document Content", "text": DocumentParser._clean_text(text)}]

    @staticmethod
    def _clean_text(text: str) -> str:
        """Removes extraction artifacts, multiple spaces, blank lines."""
        text = re.sub(r'[\r\t]', ' ', text)
        text = re.sub(r' +', ' ', text)
        text = re.sub(r'\n\s*\n+', '\n\n', text)
        return text.strip()
