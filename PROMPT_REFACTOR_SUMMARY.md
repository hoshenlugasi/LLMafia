# Prompt Refactor Summary - Social Turing Test Agent

## Overview
This document summarizes the major prompt engineering refactor implemented to improve the Social Turing Test AI agent's behavior and maintainability.

## Date
December 22, 2024

## Goals Achieved

### 1. **Clear Separation of Concerns**
- **Game Rules** → Explicit upfront explanation of the game structure
- **Identity** → Flexible, persona-specific background information
- **Behavior** → Shared guidelines for all personas

### 2. **Reduced Repetition and Rigidity**
- Removed prescriptive "NEVER/ALWAYS" language where not critical
- Clarified that examples are inspiration, not templates
- Added warnings against mechanical repetition of phrases

### 3. **Flexible Persona System**
- Supports any type of character (students, professionals, creatives, etc.)
- Response examples are now persona-specific
- Easy to add new personas without code changes

### 4. **Improved Context Understanding**
- Explicit instruction to ignore Game-Manager messages for conversation context
- Clear explanation that AI is the impostor
- Voting silence handled automatically by system

## Key Changes

### File: `llm_players/llm_constants.py`

#### New Components:

1. **GAME_RULES_PROMPT** (new)
   - Explains game structure upfront
   - Clarifies AI's role as the impostor
   - Explicit Game-Manager handling instructions
   - Placed FIRST in system prompt

2. **Flexible Persona Schema**
   ```python
   {
     "core_identity": {
       "nationality": "...",
       "age_range": "...",
       "occupation": "..."
     },
     "communication_style": {
       "english_variant": "..."
     },
     "response_examples": {
       "quick_reactions": [...],
       "when_asked_location": [...],
       "when_asked_age": [...],
       "when_asked_occupation": [...]
     }
   }
   ```

3. **build_identity_section()** (refactored)
   - Dynamically builds identity from persona config
   - Supports any occupation type (not just students)
   - Includes persona-specific response examples
   - Compact, focused presentation

4. **STYLE_AND_BEHAVIOR_GUIDELINES** (enhanced)
   - Added "Identity in Conversation" section
   - Emphasizes NOT volunteering personal info
   - Clarifies brief responses when directly asked
   - Maintained minimal structure to preserve AI variety

5. **build_system_prompt()** (simplified)
   - Clean assembly following proper order:
     1. Game Rules
     2. Identity (persona-specific)
     3. Behavior Guidelines

### File: `configurations/personas.json`

#### Updated Schema:
- Converted from old format to new flexible structure
- Added 8 diverse personas:
  - israeli_student (default)
  - american_student
  - british_student
  - australian_student
  - tech_professional
  - creative_professional
  - canadian_student
  - european_student

#### Each Persona Includes:
- Core identity traits (nationality, age, occupation)
- Communication style preferences
- Persona-specific response examples
- Quick reactions tailored to character

## Prompt Architecture

### Final System Prompt Order:
```
1. GAME_RULES_PROMPT
   ├─ Game structure
   ├─ AI role clarification
   └─ Game-Manager instructions

2. IDENTITY_SECTION (from persona)
   ├─ Core identity
   ├─ Communication style
   └─ Response examples (persona-specific)

3. STYLE_AND_BEHAVIOR_GUIDELINES
   ├─ Identity in conversation
   ├─ Core priorities
   ├─ Message evaluation checklist
   ├─ Decision guidelines
   ├─ Style & naturalness
   └─ Handling AI accusations
```

## Benefits

### 1. **Maintainability**
- Easy to add new personas
- Clear separation of game rules vs. behavior
- Single source of truth for each component

### 2. **Flexibility**
- Support any character type (students, professionals, creatives)
- Persona-specific examples prevent one-size-fits-all approach
- Easy to experiment with different identities

### 3. **Reduced Repetition**
- Multiple diverse examples per persona
- Strong warnings against mechanical copying
- Emphasis on variation and naturalness

### 4. **Better AI Understanding**
- Clear game structure explanation
- Explicit context handling (ignore Game-Manager)
- Identity vs. behavior distinction

### 5. **Consistency Across Tasks**
- Same prompt structure for scheduling and generation
- Cleaner mental model for the LLM
- Predictable behavior patterns

## Backward Compatibility

- Existing configs will continue to work
- Default persona (`israeli_student`) maintains similar behavior
- `GENERAL_SYSTEM_INFO` constant preserved for legacy code
- Fallback persona in `get_persona()` uses new schema

## Usage

### To Use a Specific Persona:
```python
llm_config = {
    ...
    "persona": "tech_professional"  # or any persona ID
}
```

### To Add a New Persona:
1. Add entry to `configurations/personas.json`
2. Follow the schema structure
3. Provide persona-specific response examples
4. No code changes needed

## Testing Recommendations

1. **Test with different personas** to ensure flexibility works
2. **Monitor for repetition** - verify warnings are effective
3. **Check identity disclosure** - ensure AI doesn't volunteer info
4. **Verify context handling** - Game-Manager messages properly ignored
5. **Evaluate naturalness** - responses should vary appropriately

## Future Enhancements

- Add more diverse persona types (teachers, retail workers, etc.)
- Collect data on which personas perform best
- Fine-tune response examples based on game outcomes
- Consider regional slang variations
- Add occupation-specific knowledge hints

## Notes

- Response examples are intentionally brief (6 items max) to avoid over-constraining the AI
- Identity section kept minimal to preserve variety
- Behavior guidelines remain shared across personas for consistency
- Anti-repetition warnings placed strategically throughout prompt

---

**Implementation Date:** December 22, 2024  
**Files Modified:**
- `llm_players/llm_constants.py`
- `configurations/personas.json`
- `PROMPT_REFACTOR_SUMMARY.md` (this file - new)
