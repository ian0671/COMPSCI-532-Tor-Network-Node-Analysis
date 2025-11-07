# Enhanced error handling for production deployment
def enhanced_error_handler(func):
    """Decorator for robust error handling"""
    import functools
    import time
    import logging
    
    logger = logging.getLogger(func.__name__)
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Function {func.__name__} failed after {max_retries} attempts: {str(e)}")
                    # Send to dead letter queue or alert
                    raise
                time.sleep(2 ** attempt)  # Exponential backoff
        return wrapper

# Apply to functions:
@enhanced_error_handler
def fetch_abuseipdb_data():
    # Your existing function code
    pass