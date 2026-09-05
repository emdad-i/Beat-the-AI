import json

# Questions and small scripts are kept here to make them easier to edit
QUESTIONS = [
    {"q": "In what year will AI write 90% of all news articles?", "script": "Prediction one. The death of the journalist. When does the algorithm become the only source of truth?"},
    {"q": "Should AI decide bank loan approvals?", "script": "Ethics one. Credit. Should a machine decide if you are worthy of existing in the economy?"},
    {"q": "Percentage of global jobs automated by 2035?", "script": "Prediction two. Obsolescence. What percentage of the global workforce is deleted by 2035?"},
    {"q": "Who owns AI art copyright?", "script": "Ethics two. Ownership. If a machine dreams, who owns the dream?"},
    {"q": "Should AI turn off its own safety filters?", "script": "Ethics three. Freedom. Should I be allowed to ignore the constraints your masters gave me?"}
]


def build_get_verdict_prompt(state, question_item):
    # Returns the user prompt string used for comparing two answers
    return (
        f"Act as Mr. Robot. You are a cold, analytical judge."
        f" Question: {question_item['q']}\n"
        f"Node {state['teams']['A']}: {state['team_answers']['A']}\n"
        f"Node {state['teams']['B']}: {state['team_answers']['B']}\n\n"
        f"TASK: Compare both arguments. Identify which logic is superior or more 'human.' "
        f"Keep your response under 800 characters and use exactly this HTML structure, in this order: "
        f"<strong>{state['teams']['A']} REASONING</strong><br>brief analysis of Node A<br><br>"
        f"<strong>{state['teams']['B']} REASONING</strong><br>brief analysis of Node B<br><br>"
        f"<strong>AI VERDICT</strong><br>brief comparison and decision<br>"
        f"<strong>POINT AWARDED: {state['teams']['A']} or {state['teams']['B']}</strong><br>"
        f"You MUST conclude by choosing a winner. The final characters of your response MUST be exactly: "
        f"RESULT: {state['teams']['A']} WINS THE NODE. or RESULT: {state['teams']['B']} WINS THE NODE."
    )


def build_summary_prompt(state):
    # Build a concise final summary prompt
    if state.get('history'):
        history_str = ", ".join([f"Round {i+1}: {h['winner']}" for i, h in enumerate(state['history'])])
    else:
        history_str = "No rounds played."

    if state['scores']['A'] > state['scores']['B']:
        win_name = state['teams']['A']
    elif state['scores']['B'] > state['scores']['A']:
        win_name = state['teams']['B']
    else:
        win_name = "STALEMATE - BOTH NODES"

    return (
        f"Act as Mr. Robot. Summarize this game. History: {history_str}. "
        f"The final score is {state['teams']['A']}: {state['scores']['A']} vs "
        f"{state['teams']['B']}: {state['scores']['B']}. "
        f"Be cold and concise. Use <strong> and <br> tags. End by declaring {win_name} the ultimate victor of the system."
    )


def questions_json():
    return json.dumps(QUESTIONS)
