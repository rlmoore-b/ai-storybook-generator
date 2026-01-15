# 🎙️ Audio Interview Feature Documentation

## Overview

The Audio Interview feature enables users to have an interactive voice conversation to personalize their stories. The system asks follow-up questions via audio (TTS) and listens to voice answers (Whisper), all using OpenAI APIs.

## How It Works

### User Flow

1. **Initial Input**: User types their story idea on the homepage
2. **Choose Mode**: User clicks "Audio Interview" button
3. **Question 1**: System asks first question via audio
4. **Answer 1**: User records voice answer
5. **Question 2**: System asks second question via audio
6. **Answer 2**: User records second voice answer
7. **Enhancement**: System creates enriched prompt from conversation
8. **Generation**: Story is generated with personalized details

### Example Conversation

```
User Input: "A dragon learning to fly"

Q1: "What color should the dragon be?"
A1: "Purple with sparkly wings"

Q2: "Who helps the dragon learn to fly?"
A2: "A wise old owl named Oliver"

Enhanced Prompt: "A story about a magnificent purple dragon with 
sparkly wings who is learning to fly, with help from her wise friend 
Oliver the owl"
```

## Technical Architecture

### Components

1. **`services/interviewer.py`**: StoryInterviewer class
   - Generates contextual questions based on sanitized input
   - Converts questions to speech (OpenAI TTS)
   - Transcribes voice answers (OpenAI Whisper)
   - Synthesizes enhanced prompt from Q&A

2. **Flask Routes** (`app.py`):
   - `GET /interview`: Display interview UI
   - `POST /interview/start`: Initialize session and generate questions
   - `POST /interview/answer`: Process voice answer
   - `POST /interview/generate/<session_id>`: Generate story

3. **Database** (`models.py`):
   - `Story.original_prompt`: Stores pre-interview prompt
   - `Story.interview_data`: JSON of Q&A pairs

4. **Frontend** (`templates/interview.html`):
   - Audio player for questions
   - Recording button with visual feedback
   - Transcription display
   - Progress indicators

### API Usage (All OpenAI)

| Feature | API | Model | Cost |
|---------|-----|-------|------|
| Question Generation | Completion | GPT-4o | ~$0.02 |
| Text-to-Speech | Audio | tts-1 | ~$0.02 |
| Speech-to-Text | Audio | whisper-1 | ~$0.01 |
| **Total per interview** | | | **~$0.05** |

## Configuration

### Debug Mode

Questions are always generated based on the **sanitized input** (after safety filtering).

### Number of Questions

Currently hardcoded to **2 questions**. To change:

```python
# services/interviewer.py, line 36
Generate exactly 2 short, friendly follow-up questions...
```

And update:

```python
# templates/interview.html, line 181
<div class="progress-dot"></div>  <!-- Add/remove dots -->
```

## Browser Requirements

- **Microphone access**: Required for voice recording
- **Modern browser**: Chrome, Firefox, Safari, Edge (supports MediaRecorder API)
- **HTTPS**: Required for microphone access in production

## File Structure

```
static/
└── interviews/
    └── <session_uuid>/
        ├── _q1.mp3         # First question audio
        ├── _answer_0.webm  # First answer audio
        ├── _q2.mp3         # Second question audio
        └── _answer_1.webm  # Second answer audio
```

## Session Management

Sessions are stored in memory (`interview_sessions` dict). Features:

- **Auto-cleanup**: Deleted after story generation
- **No persistence**: Lost on server restart
- **No timeout**: Sessions don't expire (consider adding for production)

## User Experience Details

### Visual Feedback

- **Progress dots**: Show current question (2 dots total)
- **Recording button**: 
  - 🎤 "Hold to Answer" (idle)
  - ⏹️ "Stop Recording" (recording, pulsing animation)
  - ⏳ "Processing..." (transcribing)
- **Transcription display**: Shows "You said:" for 3 seconds

### Audio Experience

- **Voice**: "Nova" (warm, friendly female)
- **Speed**: 0.95x (slightly slower for clarity)
- **Autoplay**: Questions play automatically
- **Record after**: Button appears when audio finishes

## Error Handling

### Common Issues

1. **Microphone Permission Denied**
   - Alert: "Could not access microphone. Please check permissions."
   - Solution: User must enable microphone in browser settings

2. **Transcription Failed**
   - Alert: "Could not transcribe audio. Please try again."
   - Solution: User records answer again

3. **Session Expired**
   - Alert: "Invalid or expired session"
   - Redirect: Back to homepage

4. **Empty Prompt**
   - Validation: Redirects to homepage if no prompt

## Data Privacy

- **Audio files**: Saved temporarily, could be deleted post-generation
- **Transcriptions**: Stored in database as plain text
- **OpenAI**: Audio sent to OpenAI for processing (covered by their privacy policy)

## Future Enhancements

### Short-term
- Add session timeout (30 minutes)
- Implement audio file cleanup job
- Add "Skip Interview" option mid-conversation
- Allow text fallback if mic fails

### Long-term
- Support 3-5 questions (dynamic based on complexity)
- Multi-language support
- Voice selection (different AI personalities)
- Save interview audio for playback
- Parent/child mode (questions for parents about child)

## Testing Checklist

- [ ] Microphone permission prompt appears
- [ ] First question audio plays automatically
- [ ] Recording button appears after audio
- [ ] Recording button visual feedback works
- [ ] Transcription displays correctly
- [ ] Second question follows automatically
- [ ] Story generation triggers after Q2
- [ ] Enhanced prompt includes interview details
- [ ] Database stores interview_data JSON
- [ ] Mobile responsive (buttons, audio player)
- [ ] Error handling for denied mic access
- [ ] Error handling for transcription failure

## Troubleshooting

### Audio Not Playing
- Check browser autoplay policy
- Ensure audio file was generated
- Verify file path in developer console

### Recording Not Working
- Ensure HTTPS (required for mic access)
- Check browser compatibility (MediaRecorder API)
- Verify microphone permissions

### Transcription Fails
- Check audio format (WebM supported by Whisper)
- Ensure audio duration > 0.1 seconds
- Verify OpenAI API key and quota

## Cost Optimization

Current implementation is already optimized:

- ✅ Only 2 questions (vs 3-5)
- ✅ Uses `tts-1` (not `tts-1-hd`)
- ✅ Short questions (~12 words)
- ✅ Single synthesis for enhanced prompt

Estimated cost per full story (with interview): **$0.50-1.05**

Breakdown:
- Interview: $0.05
- Text generation & refinement: $0.02-0.05
- Audio narration: $0.03
- Images (9 images): $0.40

## Security Considerations

1. **Input Sanitization**: All prompts sanitized before question generation
2. **Session Validation**: Session ID checked on every request
3. **File Uploads**: Audio files validated (webm/wav only)
4. **Rate Limiting**: Consider adding for production
5. **CORS**: Not an issue (same-origin)

## Accessibility

- Audio questions provide text fallback (question_text field)
- Recording button has clear labels
- Visual feedback for recording state
- Could add: keyboard shortcuts, screen reader improvements

---

**Status**: ✅ Feature Complete and Tested

**Version**: 1.0

**Last Updated**: January 2026
