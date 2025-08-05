from langchain.prompts import ChatPromptTemplate

member_list_prompt = ChatPromptTemplate.from_template("""
तुमच्याकडे मंत्र्यांची आणि इतर सदस्यांची यादी आहे. कृपया खालील मजकुरामधून प्रत्येक व्यक्तीबाबतची माहिती गोळा करा आणि खाली दिलेल्या JSON स्वरूपात उत्तर द्या.

प्रत्येक नोंदीसाठी खालील माहिती मिळवण्याचा प्रयत्न करा:
- "name" (उदाहरण: श्री. अजित अनंतराव पवार)
- "position" (उदाहरण: मुख्यमंत्री, उपमुख्यमंत्री, मंत्री, राज्यमंत्री, अध्यक्ष, इत्यादी)
- "department" (उदाहरण: गृह, नगरविकास, कृषी, ऊर्जा, इत्यादी)

Text:
{input_text}

Output format:

[
  {{
    "name": "",
    "position": "",
    "department": ""
  }},
  ...
]
""")
