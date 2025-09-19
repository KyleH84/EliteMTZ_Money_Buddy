def calculate_life_path_number(birthday):
    """
    Calculate a basic life path number from a birthday string (YYYY-MM-DD).
    """
    try:
        digits = [int(c) for c in birthday if c.isdigit()]
        while len(digits) > 1:
            digits = [int(c) for c in str(sum(digits))]
        return digits[0]
    except Exception:
        return None

def filter_by_life_path(numbers, life_path):
    if life_path is None:
        return numbers
    return [n for n in numbers if (n + life_path) % 2 == 0]