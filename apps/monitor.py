
import time
import os
import re
import sys

LOG_FILE = "logs/full_history_scan.log"
TOTAL_CHATS = 603  # Known total from logs

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def parse_log():
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        active_chats = {} # chat_index -> chat_name
        processed_chats_count = 0
        total_messages = 0
        total_leads = 0
        leads_details = {}
        
        # Track total scanned messages
        scanned_messages_count = 0
        
        for line in lines:
            # New parallel start/progress format
            # [1] ⏳ ChatName: processed 5000 msgs...
            progress_match = re.search(r'\[(\d+)\] ⏳ (.+): processed (\d+) msgs', line)
            if progress_match:
                index = int(progress_match.group(1))
                name = progress_match.group(2).strip()
                count = int(progress_match.group(3))
                active_chats[index] = f"{name} ({count})"
                # We can't easily sum active + done without overlap logic if we just iterate
                # So we will sum "DONE" lines + current active counts
                
            # Completion
            # [1] ✅ DONE: ChatName (123 msgs)
            done_match = re.search(r'\[(\d+)\] ✅ DONE: (.+) \((\d+) msgs\)', line)
            if done_match:
                index = int(done_match.group(1))
                count = int(done_match.group(3))
                processed_chats_count += 1
                scanned_messages_count += count
                if index in active_chats:
                    del active_chats[index]
            
            # Empty
            # [1] ⚪ EMPTY: ChatName
            empty_match = re.search(r'\[(\d+)\] ⚪ EMPTY:', line)
            if empty_match:
                processed_chats_count += 1
                index = int(empty_match.group(1))
                if index in active_chats:
                    del active_chats[index]
            
            # Check for found leads
            #    ✅ Найдено! Score: 4, Spec: SEO
            lead_match = re.search(r'✅ Найдено! .* Spec: (.+)', line)
            if lead_match:
                total_leads += 1
                spec = lead_match.group(1).strip()
                leads_details[spec] = leads_details.get(spec, 0) + 1
        
        # Add current active counts to total
        for chat_info in active_chats.values():
            # Extract count from "Name (123)"
            match = re.search(r'\((\d+)\)$', chat_info)
            if match:
                scanned_messages_count += int(match.group(1))

        return {
            "active_chats": list(active_chats.values()),
            "processed_chats": processed_chats_count,
            "total_chats": TOTAL_CHATS,
            "total_scanned_messages": scanned_messages_count,
            "total_leads": total_leads,
            "leads_details": leads_details
        }
    except FileNotFoundError:
        return None

def display_dashboard():
    print("🚀 ПАРАЛЛЕЛЬНОЕ СКАНИРОВАНИЕ ЗАПУЩЕНО")
    
    # Static total estimate
    TOTAL_ESTIMATED_MSGS = 2595702
    
    while True:
        data = parse_log()
        
        if not data:
            sys.stdout.write("\r⏳ Ожидание логов...")
            sys.stdout.flush()
        else:
            # Message Progress
            total_scanned = data.get('total_scanned_messages', 0)
            msg_prog = (total_scanned / TOTAL_ESTIMATED_MSGS) * 100 if TOTAL_ESTIMATED_MSGS else 0
            
            # Progress Bar
            bar_len = 20
            filled = int(bar_len * total_scanned // TOTAL_ESTIMATED_MSGS)
            bar = '█' * filled + '░' * (bar_len - filled)
            
            # Chats
            chats_done = data['processed_chats']
            total_chats = data['total_chats']
            
            # Leads
            leads = data['total_leads']
            
            # Active
            active_count = len(data['active_chats'])
            
            # Single line format
            # ⏳ 1.35% [██░░░] 35k/2.6M msgs | 5/603 chats | 260 leads | 5 threads
            output = (
                f"\r⏳ {msg_prog:5.2f}% [{bar}] "
                f"{total_scanned:,} / {TOTAL_ESTIMATED_MSGS:,} msgs | "
                f"{chats_done}/{total_chats} chats | "
                f"🎯 {leads} leads | "
                f"🌊 {active_count} thrd"
            )
            
            sys.stdout.write(output)
            sys.stdout.flush()
                
        time.sleep(0.5)

if __name__ == "__main__":
    try:
        display_dashboard()
    except KeyboardInterrupt:
        print("\n👋 Мониторинг остановлен.")
