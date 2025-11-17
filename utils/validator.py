from typing import Dict, List, Any

class BudgetValidator:
    """Validate budget calculations against formulas"""
    
    def __init__(self, inflation_rate: float = 5.0, tolerance: float = 0.5):
        self.inflation_rate = inflation_rate
        self.tolerance = tolerance
    
    def validate(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate all budget calculations"""
        
        report = {
            'student_name': extracted_data.get('student_name', 'Unknown'),
            'department': extracted_data.get('department', 'Unknown'),
            'fixed_expenses_results': [],
            'variable_expenses_results': [],
            'total_expenses_results': {},
            'correct_count': 0,
            'total_calculations': 0,
            'percentage': 0.0
        }
        
        # Validate fixed expenses
        for item in extracted_data.get('fixed_expenses', []):
            item_result = self._validate_fixed_item(item)
            report['fixed_expenses_results'].append(item_result)
            
            # Count correct/total
            for validation in item_result['validations'].values():
                report['total_calculations'] += 1
                if validation['correct']:
                    report['correct_count'] += 1
        
        # Validate variable expenses
        for item in extracted_data.get('variable_expenses', []):
            item_result = self._validate_variable_item(item)
            report['variable_expenses_results'].append(item_result)
            
            for validation in item_result['validations'].values():
                report['total_calculations'] += 1
                if validation['correct']:
                    report['correct_count'] += 1
        
        # Validate total expenses
        total_result = self._validate_total(
            extracted_data.get('total_expenses', {}),
            extracted_data.get('fixed_expenses', []),
            extracted_data.get('variable_expenses', [])
        )
        report['total_expenses_results'] = total_result
        
        for validation in total_result.values():
            report['total_calculations'] += 1
            if validation['correct']:
                report['correct_count'] += 1
        
        # Calculate percentage
        if report['total_calculations'] > 0:
            report['percentage'] = (report['correct_count'] / report['total_calculations']) * 100
        
        return report
    
    def _validate_fixed_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Validate fixed expense item calculations"""
        
        validations = {}
        
        # Get student values
        five_month = item.get('5_month_consumption')
        monthly = item.get('monthly_consumption')
        year_2024 = item.get('2024_year_consumption')
        inflation_rate = item.get('inflation_rate', self.inflation_rate)
        inflation_amount = item.get('inflation_amount')
        estimated_2025 = item.get('estimated_2025_consumption')
        
        # Validate Monthly Consumption = 5-month / 5
        if five_month is not None and monthly is not None:
            expected_monthly = five_month / 5
            validations['monthly_consumption'] = self._compare_values(
                monthly, expected_monthly, "Monthly consumption"
            )
        
        # Validate 2024 Year = Monthly × 12
        if monthly is not None and year_2024 is not None:
            expected_year = monthly * 12
            validations['2024_year_consumption'] = self._compare_values(
                year_2024, expected_year, "2024 year consumption"
            )
        
        # Validate Inflation Amount = 2024 Year × (rate / 100)
        if year_2024 is not None and inflation_amount is not None:
            expected_inflation = year_2024 * (inflation_rate / 100)
            validations['inflation_amount'] = self._compare_values(
                inflation_amount, expected_inflation, "Inflation amount"
            )
        
        # Validate 2025 Estimate = 2024 Year + Inflation
        if year_2024 is not None and inflation_amount is not None and estimated_2025 is not None:
            expected_2025 = year_2024 + inflation_amount
            validations['estimated_2025_consumption'] = self._compare_values(
                estimated_2025, expected_2025, "Estimated 2025 consumption"
            )
        
        return {
            'description': item.get('description', 'Unknown'),
            'validations': validations
        }
    
    def _validate_variable_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Validate variable expense item calculations"""
        
        validations = {}
        
        # Get student values
        five_month = item.get('5_month_consumption')
        five_month_days = item.get('5_month_patient_days')
        per_day = item.get('consumption_per_patient_day')
        yearly_days = item.get('estimated_2025_yearly_pt_days')
        amount_yearly = item.get('amount_per_yearly_pt_days')
        inflation_rate = item.get('inflation_rate', self.inflation_rate)
        inflation_amount = item.get('inflation_amount')
        total = item.get('total_amount')
        
        # NEW: Validate Estimated 2025 yearly pt days = (5-month pt days ÷ 5) × 12
        if five_month_days is not None and yearly_days is not None:
            expected_yearly_days = (five_month_days / 5) * 12
            validations['estimated_2025_yearly_pt_days'] = self._compare_values(
                yearly_days, expected_yearly_days, "Estimated 2025 yearly patient days"
            )
        
        # Validate Consumption per Patient Day = 5-month / 5-month days
        if five_month is not None and five_month_days is not None and per_day is not None:
            expected_per_day = five_month / five_month_days
            validations['consumption_per_patient_day'] = self._compare_values(
                per_day, expected_per_day, "Consumption per patient day"
            )
        
        # Validate Amount per Yearly Days = Per day × Yearly days
        if per_day is not None and yearly_days is not None and amount_yearly is not None:
            expected_yearly = per_day * yearly_days
            validations['amount_per_yearly_pt_days'] = self._compare_values(
                amount_yearly, expected_yearly, "Amount per yearly patient days"
            )
        
        # Validate Inflation Amount = Amount yearly × (rate / 100)
        if amount_yearly is not None and inflation_amount is not None:
            expected_inflation = amount_yearly * (inflation_rate / 100)
            validations['inflation_amount'] = self._compare_values(
                inflation_amount, expected_inflation, "Inflation amount"
            )
        
        # Validate Total = Amount yearly + Inflation
        if amount_yearly is not None and inflation_amount is not None and total is not None:
            expected_total = amount_yearly + inflation_amount
            validations['total_amount'] = self._compare_values(
                total, expected_total, "Total amount"
            )
        
        return {
            'description': item.get('description', 'Unknown'),
            'validations': validations
        }
    
    def _validate_total(
        self, 
        total_data: Dict[str, Any],
        fixed_items: List[Dict[str, Any]],
        variable_items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Validate total expenses calculations"""
        
        validations = {}
        
        # Get student values
        five_month = total_data.get('5_month_consumption')
        yearly = total_data.get('yearly_consumption')
        inflation_rate = total_data.get('inflation_rate', self.inflation_rate)
        inflation_amount = total_data.get('inflation_amount')
        total = total_data.get('total_amount')
        
        # Calculate expected 5-month total
        expected_five_month = 0
        for item in fixed_items:
            if item.get('5_month_consumption'):
                expected_five_month += item['5_month_consumption']
        for item in variable_items:
            if item.get('5_month_consumption'):
                expected_five_month += item['5_month_consumption']
        
        if five_month is not None:
            validations['5_month_consumption'] = self._compare_values(
                five_month, expected_five_month, "Total 5-month consumption"
            )
        
        # Calculate expected yearly total
        # Yearly = (Total fixed 2024-year) + (Total variable amount per yearly pt days)
        expected_yearly = 0
        for item in fixed_items:
            if item.get('2024_year_consumption'):
                expected_yearly += item['2024_year_consumption']
        for item in variable_items:
            if item.get('amount_per_yearly_pt_days'):
                expected_yearly += item['amount_per_yearly_pt_days']
        
        if yearly is not None:
            validations['yearly_consumption'] = self._compare_values(
                yearly, expected_yearly, "Total yearly consumption"
            )
        
        # Validate Inflation Amount = Yearly × (rate / 100)
        if yearly is not None and inflation_amount is not None:
            expected_inflation = yearly * (inflation_rate / 100)
            validations['inflation_amount'] = self._compare_values(
                inflation_amount, expected_inflation, "Total inflation amount"
            )
        
        # Validate Total = Yearly + Inflation
        if yearly is not None and inflation_amount is not None and total is not None:
            expected_total = yearly + inflation_amount
            validations['total_amount'] = self._compare_values(
                total, expected_total, "Grand total amount"
            )
        
        return validations
    
    def _compare_values(self, actual: float, expected: float, field_name: str) -> Dict[str, Any]:
        """Compare actual vs expected value with tolerance"""
        
        if actual is None:
            return {
                'correct': False,
                'status': f'⚠️ Missing value',
                'expected': round(expected, 2),
                'actual': None
            }
        
        difference = abs(actual - expected)
        is_correct = difference <= self.tolerance
        
        return {
            'correct': is_correct,
            'status': '✅ Correct' if is_correct else f'❌ Incorrect (off by {difference:.2f})',
            'expected': round(expected, 2),
            'actual': round(actual, 2)
        }