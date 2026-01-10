# Design Rationale & Architecture

## Core Philosophy
The interface serves as a "Cognitive Scaffold" rather than a tool. It minimizes visual noise to reduce cognitive load. The strict separation of "Input" (User) and "Output" (AI) preserves user agency.

## Visual Language
- **Palette**: Paper-like backgrounds (#F9F9F7), Ink-like text (#2C2C2C), Subtle functional accents (Slate Blue for modes, Warm Grey for borders).
- **Typography**: 
  - *Serif* (e.g., Literata/Merriweather) for User Text/Reading -> Promotes deep reading.
  - *Sans-Serif* (e.g., Inter/System) for UI Controls/Metadata -> distinct from content.

## Component Architecture
Components are state-agnostic views that render based on passed data.
event-driven communication via a central `App` controller.

1. **KnowledgeBase**: 
   - Visual: Clean vertical list, minimal icons. 
   - Behavior: Drag-and-drop zone opacity changes.
2. **Workspace**: 
   - Visual: Centered, distraction-free page.
   - Behavior: Auto-expanding textarea/contenteditable.
3. **ModeSelector**: 
   - Visual: Pill-shaped toggle group. High contrast for "Active".
   - Constraint: Block assistance until selection.
4. **TransparencyPanel**:
   - Visual: Right sidebar, initially collapsed or low-profile.
   - Content: Citations mapping directly to Output sections.
5. **OutputPanel**:
   - Visual: Distinct background (e.g., pale warm gray) to differentiate from User text.

## Interaction Flow
- No "streaming" animations that mimic typing (human-like). Instead, block appearances or fast fades.
- Explicit "Copy to Editor" actions.

## Hallucination Prevention
- The "Transparency Panel" is not an afterthought; it is visually weighted equal to the Output.
- Metadata (Page #, Score) is prominently displayed next to every AI claim.
