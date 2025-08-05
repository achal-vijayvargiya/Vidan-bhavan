import re
from collections import Counter
from typing import Tuple, Dict

def optimize_tokens(text: str) -> Tuple[str, Dict[int, str]]:
    # Tokenize words (preserve unicode, ignore punctuation)
    words = re.findall(r'\w+', text, flags=re.UNICODE)
    # Only consider words longer than 2 characters
    words = [w for w in words if len(w) > 2]
    # Count word frequencies
    word_counts = Counter(words)
    # Get top 10 most common words
    top_words = [word for word, _ in word_counts.most_common(10)]
    # Create mapping {1: 'top word', ...}
    mapping = {i+1: word for i, word in enumerate(top_words)}
    # Replace top words in text with their mapping keys
    def replace_word(match):
        word = match.group(0)
        for k, v in mapping.items():
            if word == v:
                return str(k)
        return word
    # Use regex to replace only whole words
    pattern = r'\b(' + '|'.join(re.escape(word) for word in top_words) + r')\b'
    converted_text = re.sub(pattern, replace_word, text)
    return converted_text, mapping 