from langchain.tools import tool

NOTES_FILE = "notes.txt"

@tool
def add_note(note: str) -> str:
    with open(NOTES_FILE, "a") as f:
        f.write(note + "\n")
    return "Note added."

@tool
def get_notes(_) -> str:
    try:
        with open(NOTES_FILE, "r") as f:
            notes = f.readlines()
        return "".join(notes) if notes else "No notes found."
    except FileNotFoundError:
        return "No notes found."
