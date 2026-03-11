import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from systems.parser.vacancy_analyzer.contact_extractor import ContactExtractor

extractor = ContactExtractor()
msg_data = {
    'text': 'Всем привет \n Нужен спец по сбору данных. Есть такие?',
    'buttons': '',
    'sender_id': 123456789,
    'sender_username': None,
    'fwd_from': None
}
print(extractor.extract_contact(msg_data))
