import docx
import openpyxl
from pypdf import PdfReader
import re
import pandas as pd
from typing import Dict, List, Any

class DocumentParser:
    """Parse Word, Excel, and PDF documents to extract budget data"""
    
    def __init__(self):
        self.supported_formats = ['.docx', '.xlsx', '.pdf']
    
    def parse(self, uploaded_file) -> Dict[str, Any]:
        """Main parsing function - routes to appropriate parser"""
        file_extension = uploaded_file.name.split('.')[-1].lower()
        
        if file_extension == 'docx':
            return self.parse_word(uploaded_file)
        elif file_extension == 'xlsx':
            return self.parse_excel(uploaded_file)
        elif file_extension == 'pdf':
            return self.parse_pdf(uploaded_file)
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")
    
    def parse_word(self, uploaded_file) -> Dict[str, Any]:
        """Parse Word document"""
        doc = docx.Document(uploaded_file)
        
        # Extract student info
        full_text = '\n'.join([para.text for para in doc.paragraphs])
        student_name = self._extract_student_name(full_text)
        department = self._extract_department(full_text)
        
        # Extract tables
        tables_data = []
        for table in doc.tables:
            table_data = []
            for row in table.rows:
                row_data = [cell.text.strip() for cell in row.cells]
                table_data.append(row_data)
            tables_data.append(table_data)
        
        # Parse budget data from tables
        parsed_data = self._parse_budget_tables(tables_data)
        
        return {
            'student_name': student_name,
            'department': department,
            **parsed_data
        }
    
    def parse_excel(self, uploaded_file) -> Dict[str, Any]:
        """Parse Excel document"""
        wb = openpyxl.load_workbook(uploaded_file)
        ws = wb.active
        
        # Extract all data
        all_data = []
        for row in ws.iter_rows(values_only=True):
            all_data.append(list(row))
        
        # Extract student info from first few rows
        full_text = ' '.join([str(cell) for row in all_data[:10] for cell in row if cell])
        student_name = self._extract_student_name(full_text)
        department = self._extract_department(full_text)
        
        # Parse budget tables
        parsed_data = self._parse_budget_tables([all_data])
        
        return {
            'student_name': student_name,
            'department': department,
            **parsed_data
        }
    
    def parse_pdf(self, uploaded_file) -> Dict[str, Any]:
        """Parse PDF document"""
        pdf_reader = PdfReader(uploaded_file)
        
        # Extract text from all pages
        full_text = ''
        for page in pdf_reader.pages:
            full_text += page.extract_text()
        
        student_name = self._extract_student_name(full_text)
        department = self._extract_department(full_text)
        
        # For PDFs, we'll rely more on AI extraction since table parsing is harder
        # Return raw text for AI to process
        return {
            'student_name': student_name,
            'department': department,
            'raw_text': full_text,
            'needs_ai_extraction': True
        }
    
    def _extract_student_name(self, text: str) -> str:
        """Extract student name from text"""
        # Common patterns
        patterns = [
            r'(?:Student|Name|By|Author):\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
            r'^([A-Z][a-z]+\s+[A-Z][a-z]+)',  # First line with capitalized name
            r'([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*\n',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.MULTILINE)
            if match:
                return match.group(1).strip()
        
        return "Unknown Student"
    
    def _extract_department(self, text: str) -> str:
        """Extract department/unit from text"""
        # Look for department keywords
        dept_keywords = [
            'Emergency Department', 'ED', 'ER', 'Emergency Room',
            'Neonatal Intensive Care', 'NICU', 'ICU',
            'Pediatric', 'Surgical', 'Medical',
            'Nursing', 'HSON', 'Hariri School'
        ]
        
        for keyword in dept_keywords:
            if keyword.lower() in text.lower():
                # Try to extract full context
                pattern = rf'([^.]*{re.escape(keyword)}[^.]*)'
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    return match.group(1).strip()[:100]  # Limit length
        
        return "Unknown Department"
    
    def _parse_budget_tables(self, tables_data: List[List[List[str]]]) -> Dict[str, Any]:
        """Parse budget tables to extract structured data"""
        
        result = {
            'fixed_expenses': [],
            'variable_expenses': [],
            'total_expenses': {},
            'patient_days_initial': None
        }
        
        for table in tables_data:
            if not table or len(table) < 2:
                continue
            
            # Identify table type by headers
            headers = [str(cell).lower().strip() for cell in table[0]]
            
            # Check if it's Fixed Expenses table
            if any('fixed' in h for h in headers) or \
               (any('monthly consumption' in h for h in headers) and 
                any('2024' in h for h in headers)):
                result['fixed_expenses'] = self._parse_fixed_table(table)
            
            # Check if it's Variable Expenses table
            elif any('variable' in h for h in headers) or \
                 any('patient day' in h for h in headers):
                result['variable_expenses'] = self._parse_variable_table(table)
            
            # Check if it's Total Expenses table
            elif any('total' in h and 'expense' in h for h in headers):
                result['total_expenses'] = self._parse_total_table(table)
            
            # Check for initial patient days table
            elif any('patient days' in str(cell).lower() for row in table for cell in row):
                result['patient_days_initial'] = self._extract_patient_days(table)
        
        return result
    
    def _parse_fixed_table(self, table: List[List[str]]) -> List[Dict[str, Any]]:
        """Parse fixed expenses table"""
        fixed_items = []
        
        # Skip header row
        for row in table[1:]:
            if not row or len(row) < 6:
                continue
            
            # Clean and convert values
            try:
                item = {
                    'description': self._clean_text(row[0]),
                    '5_month_consumption': self._parse_number(row[1]),
                    'monthly_consumption': self._parse_number(row[2]),
                    '2024_year_consumption': self._parse_number(row[3]),
                    'inflation_rate': self._parse_number(row[4]),
                    'inflation_amount': self._parse_number(row[5]),
                    'estimated_2025_consumption': self._parse_number(row[6]) if len(row) > 6 else None
                }
                
                # Only add if we have valid data
                if item['description'] and item['description'].lower() not in ['total', '']:
                    fixed_items.append(item)
            except (ValueError, IndexError):
                continue
        
        return fixed_items
    
    def _parse_variable_table(self, table: List[List[str]]) -> List[Dict[str, Any]]:
        """Parse variable expenses table"""
        variable_items = []
        
        for row in table[1:]:
            if not row or len(row) < 7:
                continue
            
            try:
                item = {
                    'description': self._clean_text(row[0]),
                    '5_month_consumption': self._parse_number(row[1]),
                    '5_month_patient_days': self._parse_number(row[2]),
                    'consumption_per_patient_day': self._parse_number(row[3]),
                    'estimated_2025_yearly_pt_days': self._parse_number(row[4]),
                    'amount_per_yearly_pt_days': self._parse_number(row[5]),
                    'inflation_rate': self._parse_number(row[6]),
                    'inflation_amount': self._parse_number(row[7]) if len(row) > 7 else None,
                    'total_amount': self._parse_number(row[8]) if len(row) > 8 else None
                }
                
                if item['description'] and item['description'].lower() not in ['total', '']:
                    variable_items.append(item)
            except (ValueError, IndexError):
                continue
        
        return variable_items
    
    def _parse_total_table(self, table: List[List[str]]) -> Dict[str, Any]:
        """Parse total expenses table"""
        # Usually just one row of totals
        for row in table[1:]:
            if not row or len(row) < 5:
                continue
            
            try:
                return {
                    '5_month_consumption': self._parse_number(row[1]),
                    'yearly_consumption': self._parse_number(row[2]),
                    'inflation_rate': self._parse_number(row[3]),
                    'inflation_amount': self._parse_number(row[4]),
                    'total_amount': self._parse_number(row[5]) if len(row) > 5 else None
                }
            except (ValueError, IndexError):
                continue
        
        return {}
    
    def _extract_patient_days(self, table: List[List[str]]) -> int:
        """Extract patient days from initial table"""
        for row in table:
            for i, cell in enumerate(row):
                if 'patient days' in str(cell).lower():
                    # Next cell should have the value
                    if i + 1 < len(row):
                        return self._parse_number(row[i + 1])
        return None
    
    def _clean_text(self, text: str) -> str:
        """Clean text from table cells"""
        if not text:
            return ""
        # Remove extra whitespace, newlines
        cleaned = ' '.join(str(text).split())
        # Remove special characters but keep alphanumeric and basic punctuation
        cleaned = re.sub(r'[^\w\s\-/(),.]', '', cleaned)
        return cleaned.strip()
    
    def _parse_number(self, value: Any) -> float:
        """Parse numeric value from string"""
        if value is None or value == '':
            return None
        
        # Convert to string and clean
        value_str = str(value).strip()
        
        # Remove currency symbols, commas, percentage signs
        value_str = re.sub(r'[$,\s%]', '', value_str)
        
        # Try to convert to float
        try:
            return float(value_str)
        except ValueError:
            return None