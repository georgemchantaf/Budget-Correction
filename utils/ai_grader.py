from typing import Dict, Any
import json
from openai import OpenAI
import requests

class AIGrader:
    """AI-powered grading using LLMs for intelligent extraction and validation"""
    
    def __init__(self, provider: str = "openai", api_key: str = None, model: str = None):
        self.provider = provider.lower()
        self.api_key = api_key
        self.model = model or self._get_default_model()
        
        # Initialize client
        if self.provider == "openai":
            self.client = OpenAI(api_key=api_key)
        elif self.provider == "anthropic":
            self.client = None
        elif self.provider == "local":
            self.ollama_url = "http://localhost:11434/api/generate"
    
    def _get_default_model(self) -> str:
        """Get default model for provider"""
        defaults = {
            "openai": "gpt-4-turbo",
            "anthropic": "claude-sonnet-4-5",
            "local": "llama3"
        }
        return defaults.get(self.provider, "gpt-4-turbo")
    
    def grade(self, extracted_data: Dict[str, Any], inflation_rate: float = 5.0, tolerance: float = 0.5) -> Dict[str, Any]:
        """Grade the assignment using AI"""
        
        # If PDF or needs AI extraction
        if extracted_data.get('needs_ai_extraction'):
            extracted_data = self._ai_extract_data(extracted_data.get('raw_text', ''))
        
        # Now validate with AI
        validation_result = self._ai_validate(extracted_data, inflation_rate, tolerance)
        
        return validation_result
    
    def _ai_extract_data(self, raw_text: str) -> Dict[str, Any]:
        """Use AI to extract structured data from raw text"""
        
        system_prompt = """You are a nursing budget data extraction assistant. Extract ALL numerical data from the student's supplies budget assignment.

The assignment contains 3 tables:
1. **Fixed Expenses** with columns: 5-month consumption, Monthly consumption, 2024-year consumption, Inflation rate, Inflation amount, Estimated 2025-year consumption
2. **Variable Expenses** with columns: 5-month consumption, 5-month patient days, Consumption per patient day, Estimated 2025 yearly pt. days, Amount per yearly pt. days, Inflation rate, Inflation amount, Total amount
3. **Total Expenses** with columns: 5-month consumption, Yearly consumption, Inflation rate, Inflation amount, Total amount

Extract and output as JSON with this EXACT structure:

{
  "student_name": "Student Full Name",
  "department": "Department/Unit Name",
  "fixed_expenses": [
    {
      "description": "Office Supplies",
      "5_month_consumption": 500,
      "monthly_consumption": 100,
      "2024_year_consumption": 1200,
      "inflation_rate": 5,
      "inflation_amount": 60,
      "estimated_2025_consumption": 1260
    }
  ],
  "variable_expenses": [
    {
      "description": "Medical/Surgical Supplies",
      "5_month_consumption": 20000,
      "5_month_patient_days": 1000,
      "consumption_per_patient_day": 20,
      "estimated_2025_yearly_pt_days": 24000,
      "amount_per_yearly_pt_days": 480000,
      "inflation_rate": 5,
      "inflation_amount": 24000,
      "total_amount": 504000
    }
  ],
  "total_expenses": {
    "5_month_consumption": 37750,
    "yearly_consumption": 90600,
    "inflation_rate": 5,
    "inflation_amount": 4530,
    "total_amount": 95130
  },
  "patient_days_initial": 3800
}

IMPORTANT: Extract ONLY the numbers the student provided. Do NOT calculate or correct anything. If a value is missing, use null.
Return ONLY valid JSON, no markdown formatting or explanation."""

        user_prompt = f"""Extract all budget data from this assignment:

{raw_text}

Return the data as JSON following the exact structure specified."""

        # Call AI based on provider
        if self.provider == "openai":
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            result = response.choices[0].message.content
        
        elif self.provider == "anthropic":
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1
            )
            result = response.content[0].text
        
        elif self.provider == "local":
            payload = {
                "model": self.model,
                "prompt": f"{system_prompt}\n\n{user_prompt}",
                "stream": False,
                "format": "json"
            }
            response = requests.post(self.ollama_url, json=payload)
            result = response.json().get('response', '{}')
        
        # Parse JSON response
        try:
            # Clean up response (remove markdown if present)
            result = result.strip()
            if result.startswith('```json'):
                result = result[7:]
            if result.startswith('```'):
                result = result[3:]
            if result.endswith('```'):
                result = result[:-3]
            
            extracted = json.loads(result.strip())
            return extracted
        except json.JSONDecodeError as e:
            raise ValueError(f"AI returned invalid JSON: {e}\n\nResponse: {result}")
    
    def _ai_validate(self, extracted_data: Dict[str, Any], inflation_rate: float, tolerance: float) -> Dict[str, Any]:
        """Use AI to validate calculations and provide detailed feedback"""
        
        system_prompt = f"""You are a nursing budget grading assistant. Validate student calculations against these formulas:

**FIXED EXPENSES FORMULAS:**
- Monthly consumption = 5-month consumption ÷ 5
- 2024-year consumption = Monthly consumption × 12
- Inflation amount = 2024-year consumption × (Inflation rate ÷ 100)
- Estimated 2025 consumption = 2024-year consumption + Inflation amount

**VARIABLE EXPENSES FORMULAS:**
- Estimated 2025 yearly pt days = (5-month patient days ÷ 5) × 12
- Consumption per patient day = 5-month consumption ÷ 5-month patient days
- Amount per yearly pt days = Consumption per patient day × Estimated 2025 yearly pt days
- Inflation amount = Amount per yearly pt days × (Inflation rate ÷ 100)
- Total amount = Amount per yearly pt days + Inflation amount

**TOTAL EXPENSES FORMULAS:**
- 5-month consumption = Sum of all fixed 5-month + Sum of all variable 5-month
- Yearly consumption = (Total fixed 2024-year) + (Total variable amount per yearly pt days)
- Inflation amount = Yearly consumption × (Inflation rate ÷ 100)
- Total amount = Yearly consumption + Inflation amount

**GRADING RULES:**
- Expected inflation rate: {inflation_rate}%
- Allow rounding differences up to ±{tolerance}
- Each correct calculation = 1 point
- Mark as: ✅ Correct, ❌ Wrong (show expected vs actual), ⚠️ Missing

Generate a detailed grading report with:
1. Student name and department
2. Item-by-item validation for EACH expense line
3. For EACH field in EACH item, show: correct/incorrect status, expected value, actual value
4. Total score (correct / total calculations)
5. Percentage grade

Return ONLY valid JSON with this structure:

{{
  "student_name": "Name",
  "department": "Department",
  "fixed_expenses_results": [
    {{
      "description": "Office Supplies",
      "validations": {{
        "monthly_consumption": {{
          "correct": true,
          "status": "✅ Correct",
          "expected": 100,
          "actual": 100
        }},
        "2024_year_consumption": {{
          "correct": false,
          "status": "❌ Incorrect (off by 12.50)",
          "expected": 1200,
          "actual": 1212.50
        }}
      }}
    }}
  ],
  "variable_expenses_results": [ /* same structure */ ],
  "total_expenses_results": {{
    "5_month_consumption": {{ "correct": true, "status": "✅ Correct", "expected": 37750, "actual": 37750 }}
  }},
  "correct_count": 45,
  "total_calculations": 50,
  "percentage": 90.0,
  "summary": "Brief summary of performance"
}}

Be thorough - check EVERY calculation for EVERY item. Return ONLY JSON, no markdown."""

        user_prompt = f"""Validate this student's budget and provide detailed grading:

{json.dumps(extracted_data, indent=2)}

Check ALL formulas and calculations. Return detailed JSON report."""

        # Call AI
        if self.provider == "openai":
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            result = response.choices[0].message.content
        
        elif self.provider == "anthropic":
            response = self.client.messages.create(
                model=self.model,
                max_tokens=8000,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1
            )
            result = response.content[0].text
        
        elif self.provider == "local":
            payload = {
                "model": self.model,
                "prompt": f"{system_prompt}\n\n{user_prompt}",
                "stream": False,
                "format": "json"
            }
            response = requests.post(self.ollama_url, json=payload)
            result = response.json().get('response', '{}')
        
        # Parse response
        try:
            result = result.strip()
            if result.startswith('```json'):
                result = result[7:]
            if result.startswith('```'):
                result = result[3:]
            if result.endswith('```'):
                result = result[:-3]
            
            report = json.loads(result.strip())
            return report
        except json.JSONDecodeError as e:
            raise ValueError(f"AI validation returned invalid JSON: {e}\n\nResponse: {result}")