# --- GRAND TOTAL CALCULATIONS ROW EXECUTION (FIXED LOGIC) ---
card_html += '<tr style="background-color: #f5f5f5; font-weight: bold; -webkit-print-color-adjust: exact; print-color-adjust: exact;"><td style="border:1px solid #333; padding:5px 8px; text-align:left;">⚡ TOTAL</td>'
if num_selected_tests == 1:
    exam = selected_tests[0]
    exam_matches = raw_marks[raw_marks['exam_type'] == exam.strip()]
    
    # Filter out empty rows or non-numeric strings to ONLY calculate subjects the student actually took
    valid_matches = exam_matches[exam_matches['marks_obtained'].apply(lambda x: str(x).replace('.','',1).isdigit())]
    
    if not valid_matches.empty:
        t_obt = valid_matches['marks_obtained'].astype(float).sum()
        # FIX: Only sum up max marks for subjects that have valid numeric obtained scores
        t_max = valid_matches['total_marks'].astype(float).sum()
        t_pass = t_max * 0.40
        
        current_card_percentage = int((t_obt/t_max)*100) if t_max > 0 else 0
        status_str = "<span style='color:green;'>Pass</span>" if t_obt >= t_pass else "<span style='color:red;'>Fail</span>"
        
        card_html += f'<td style="border:1px solid #333; padding:5px;">{int(t_obt)}</td><td style="border:1px solid #333; padding:5px;">{int(t_max)}</td><td style="border:1px solid #333; padding:5px;">{int(t_pass)}</td><td style="border:1px solid #333; padding:5px;">{current_card_percentage}%</td><td style="border:1px solid #333; padding:5px;">{status_str}</td>'
    else:
        card_html += '<td style="border:1px solid #333; padding:5px;">-</td><td style="border:1px solid #333; padding:5px;">-</td><td style="border:1px solid #333; padding:5px;">-</td><td style="border:1px solid #333; padding:5px;">-</td><td style="border:1px solid #333; padding:5px;">-</td>'
else:
    # Multiple exam columns multi-comparison structural view layout block
    for exam in selected_tests:
        exam_matches = raw_marks[raw_marks['exam_type'] == exam.strip()]
        valid_exam_matches = exam_matches[exam_matches['marks_obtained'].apply(lambda x: str(x).replace('.','',1).isdigit())]
        
        if not valid_exam_matches.empty:
            t_obt = valid_exam_matches['marks_obtained'].astype(float).sum()
            # FIX: Match the behavior here too
            t_max = valid_exam_matches['total_marks'].astype(float).sum()
            card_html += f'<td style="border:1px solid #333; padding:5px;">{int(t_obt)}</td><td style="border:1px solid #333; padding:5px;">{int((t_obt/t_max)*100)}%</td>'
        else:
            card_html += '<td style="border:1px solid #333; padding:5px;">-</td><td style="border:1px solid #333; padding:5px;">-</td>'
    
    if grand_total_max > 0:
        current_card_percentage = int((grand_total_obtained / grand_total_max) * 100)
        card_html += f'<td style="border:1px solid #333; padding:5px;">{current_card_percentage}%</td>'
    else:
        card_html += '<td style="border:1px solid #333; padding:5px;">-</td>'

card_html += '</tr></tbody></table>'
