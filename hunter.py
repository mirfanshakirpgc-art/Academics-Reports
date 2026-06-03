with open("app.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

inside_triple_quote = False
start_line = 0

for idx, line in enumerate(lines):
    # Count how many times triple quotes appear on this line
    count = line.count('"""')
    
    # If it appears an odd number of times, it toggles our state
    if count % 2 != 0:
        if not inside_triple_quote:
            inside_triple_quote = True
            start_line = idx + 1
        else:
            inside_triple_quote = False

if inside_triple_quote:
    print(f"🚨 FOUND IT! A triple quote was opened on line {start_line} but was never closed!")
else:
    print("✨ The script didn't catch an unclosed string. Double check for unclosed single-line strings or open parentheses '(' next!")
