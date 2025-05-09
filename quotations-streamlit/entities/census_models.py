from dataclasses import dataclass, asdict
from typing import Dict, Any

@dataclass
class CensusAnalysis:
    """Data class for census analysis results"""
    census_count: int
    over_64_count: int
    pct_elderly: float
    male_count: int
    male_pct: float
    female_count: int
    female_pct: float
    married_f_under_45: int
    pct_married_f_under_45: float
    avg_adult_age: float
    principal_count: int
    principal_pct: float
    dependent_count: int
    dependent_pct: float
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the dataclass to a dictionary
        
        Returns:
            dict: Dictionary representation of the dataclass
        """
        return asdict(self)
