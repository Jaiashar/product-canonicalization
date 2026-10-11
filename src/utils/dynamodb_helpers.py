from decimal import Decimal
from typing import Any, Dict

def convert_floats_to_decimal(obj: Any) -> Any:
    """Convert all float values to Decimal for DynamoDB"""
    if isinstance(obj, float):
        return Decimal(str(round(obj, 6)))
    elif isinstance(obj, dict):
        return {key: convert_floats_to_decimal(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_floats_to_decimal(item) for item in obj]
    else:
        return obj

def convert_decimals_to_float(obj: Any) -> Any:
    """Convert Decimal values back to float for processing"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {key: convert_decimals_to_float(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals_to_float(item) for item in obj]
    else:
        return obj

def prepare_item_for_dynamodb(item: Dict) -> Dict:
    return convert_floats_to_decimal(item)

def process_item_from_dynamodb(item: Dict) -> Dict:
    return convert_decimals_to_float(item)