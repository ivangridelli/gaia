from langchain.tools import tool

NOTES_FILE = "notes.txt"

@tool
def add_note(note: str) -> str:
    """
    Add a note to the persistent notes file.

    Example usage:
    add_note("Buy groceries") -> "Note added."

    The note is appended to a text file named 'notes.txt'.
    """
    with open(NOTES_FILE, "a") as f:
        f.write(note + "\n")
    return "Note added."

@tool
def get_notes(_) -> str:
    """
    Retrieve all notes stored in the persistent notes file.

    Example usage:
    get_notes("") -> "Buy groceries\nCall Alice\n..."

    If no notes are found, returns "No notes found."
    """
    try:
        with open(NOTES_FILE, "r") as f:
            notes = f.readlines()
        return "".join(notes) if notes else "No notes found."
    except FileNotFoundError:
        return "No notes found."
