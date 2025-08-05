import re



def extract_fields_from_marathi_text(text):
    data = {}
    # 1. Date
    date_match = re.search(r'\d{1,2} [ज|फ|म|ए|म|ज|ज|ऑ|स|ऑ|नो|ड][^\s]* \d{4}', text)
    data["date"] = date_match.group() if date_match else None

    # 2. Question numbers
    question_numbers = re.findall(r'(?:प्रश्न क्रमांक|क्रमांक)\s*(\d+)', text)
    data["question_number"] = question_numbers

    # 3. Members
    members_pattern = r'(?:श्रीमती|श्री|सर्वश्री)\.? [^\n:,]+'
    members = re.findall(members_pattern, text)
    data["members"] = list(set(members))  # unique

    # 4. Topics
    topics = []
    topic_lines = text.split('\n')
    for line in topic_lines:
        if "वेतन" in line or "अनुदान" in line or "नेमणूक" in line:
            topics.append(line.strip())
    data["topics"] = list(set(topics))

    # 5. Answers by (look for names followed by colon)
    answers_by = re.findall(r'(?:श्री\.|श्रीमती\.?)\s[^\n:]+(?= :|\:)', text)
    data["answers_by"] = list(set(answers_by))

    return data