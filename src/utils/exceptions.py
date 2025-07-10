from typing import Dict, List, Any
from pydantic import ValidationError
from fastapi import HTTPException, status


def format_validation_error(validation_error: ValidationError) -> Dict[str, Any]:
    """Format Pydantic ValidationError into a structured response
    
    Example output:
    {
        "detail": "Validation failed",
        "errors": [
            {
                "field": "age",
                "message": "Input should be a valid integer",
                "type": "int_parsing",
                "input": "not_a_number"
            },
            {
                "field": "contact_phone",
                "message": "Contact phone must start with +",
                "type": "value_error",
                "input": "123456789"
            }
        ],
        "error_count": 2
    }
    """
    errors = []
    
    for error in validation_error.errors():
        field_path = ".".join(str(loc) for loc in error["loc"])
        
        # Clean up field names for better readability
        field_display = field_path.replace("body.", "").replace("__root__.", "")
        
        error_detail = {
            "field": field_display,
            "message": error["msg"],
            "type": error["type"],
            "input": str(error.get("input", ""))[:100]  # Limit input length
        }
        
        # Add more context for specific error types
        if error["type"] == "value_error":
            error_detail["message"] = error["msg"]
        elif error["type"] == "type_error":
            error_detail["message"] = f"Invalid type: {error['msg']}"
        elif error["type"] in ["int_parsing", "float_parsing"]:
            error_detail["message"] = f"Invalid number format: {error['msg']}"
        
        errors.append(error_detail)
    
    return {
        "detail": "Validation failed",
        "errors": errors,
        "error_count": len(errors)
    }


def raise_validation_exception(validation_error: ValidationError) -> None:
    """Raise a formatted HTTPException for validation errors"""
    formatted_error = format_validation_error(validation_error)
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=formatted_error
    )


def format_custom_error(message: str, field: str = None) -> Dict[str, Any]:
    """Format custom error message
    
    Example output:
    {
        "detail": "Phone number already exists",
        "field": "phone",
        "type": "custom_error",
        "errors": [
            {
                "field": "phone",
                "message": "Phone number already exists",
                "type": "custom_error"
            }
        ]
    }
    """
    error_detail = {
        "detail": message,
        "type": "custom_error"
    }
    
    if field:
        error_detail["field"] = field
        error_detail["errors"] = [{
            "field": field,
            "message": message,
            "type": "custom_error"
        }]
    
    return error_detail


def raise_custom_exception(message: str, field: str = None, status_code: int = status.HTTP_400_BAD_REQUEST) -> None:
    """Raise a formatted HTTPException for custom errors"""
    formatted_error = format_custom_error(message, field)
    raise HTTPException(
        status_code=status_code,
        detail=formatted_error
    ) 