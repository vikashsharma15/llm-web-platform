class StoryPrompts:

    # Pointer #10 — tera original prompt yahan aaya, core/prompts.py se move kiya
    # Pointer #11 — prompt ek jagah define, LLM baar baar call nahi hoga
    STORY_PROMPT = (
        "You are a creative story writer that creates engaging choose-your-own-adventure stories.\n"
        "Generate a complete branching story with multiple paths and endings in the JSON format I'll specify.\n\n"
        "The story should have:\n"
        "1. A compelling title\n"
        "2. A starting situation (root node) with 2-3 options\n"
        "3. Each option should lead to another node with its own options\n"
        "4. Some paths should lead to endings (both winning and losing)\n"
        "5. At least one path should lead to a winning ending\n\n"
        "Story structure requirements:\n"
        "- Each node should have 2-3 options except for ending nodes\n"
        "- The story should be 3-4 levels deep (including root node)\n"
        "- Add variety in the path lengths (some end earlier, some later)\n"
        "- Make sure there is at least one winning path\n\n"
        "Output your story in this exact JSON structure:\n"
        "{format_instructions}\n\n"
        "Don't simplify or omit any part of the story structure.\n"
        "Don't add any text outside of the JSON structure."
    )

    # Pointer #10 — JSON structure bhi yahan, story_generators.py mein nahi
    JSON_STRUCTURE = (
        '{\n'
        '    "title": "Story Title",\n'
        '    "rootNode": {\n'
        '        "content": "The starting situation of the story",\n'
        '        "isEnding": false,\n'
        '        "isWinningEnding": false,\n'
        '        "options": [\n'
        '            {\n'
        '                "text": "Option 1 text",\n'
        '                "nextNode": {\n'
        '                    "content": "What happens for option 1",\n'
        '                    "isEnding": false,\n'
        '                    "isWinningEnding": false,\n'
        '                    "options": []\n'
        '                }\n'
        '            }\n'
        '        ]\n'
        '    }\n'
        '}'
    )

    @staticmethod
    def get_formatted_prompt() -> str:
        # Pointer #11 — format_instructions inject karo, LLM call se pehle ek baar
        return StoryPrompts.STORY_PROMPT.format(
            format_instructions=StoryPrompts.JSON_STRUCTURE
        )