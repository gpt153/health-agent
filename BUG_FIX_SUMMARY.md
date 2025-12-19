# Bug Fix: Sleep Quiz Question 8 (Alertness) Gets Stuck

## Issue
Users reported that the sleep quiz gets stuck on the final question (Q8 - Alertness rating) with "no submit button".

## Root Cause
**UX Design Issue + Lack of Error Handling**

1. **Missing Submit Button**: Q8 showed a 1-10 rating scale but had no visible submit/confirm button
2. **User Expectation Mismatch**: Q7 (previous question) has a "✅ Done" button, leading users to expect one on Q8
3. **Silent Failures**: No error handling meant any exception would fail silently, making the quiz appear "stuck"

## Fixes Implemented

### 1. Added Submit Button with Two-Step Flow
**File**: `src/handlers/sleep_quiz.py`

**Changes to `show_alertness_question()` (lines 415-451)**:
- Added logic to detect if user has made a selection
- Dynamically adds "✅ Submit" button after selection
- Shows clear instructions: "Select a number below" → "Click submit to complete"
- Displays current selection to user

**User Flow**:
1. User sees Q8 with 1-10 rating buttons
2. User clicks a number (e.g., "7")
3. Question updates to show:
   - "Selected: 7/10"
   - "✅ Submit" button appears
   - Instruction: "Click submit to complete, or select a different rating"
4. User can change selection or click Submit
5. Quiz completes on Submit

### 2. Added Comprehensive Error Handling
**Changes to `handle_alertness_callback()` (lines 454-596)**:

Added try/except blocks for:
- **KeyError**: Missing required quiz data fields
- **ValueError**: Invalid data format
- **Exception**: Any other unexpected errors

**Error Responses**:
- Clear error messages to user
- Graceful cleanup of quiz state
- Detailed logging for debugging
- Instruction to restart quiz with /sleep_quiz

### 3. Added Data Validation
**Changes to `handle_alertness_callback()`**:

Validates required fields before processing:
- `bedtime`
- `wake_time`
- `sleep_latency_minutes`
- `sleep_quality_rating`
- `phone_usage`

If any field is missing:
- Logs error with field names
- Shows user-friendly error message
- Lists missing fields (for debugging)
- Cleans up quiz state

### 4. Improved Callback Logic
**Changes to `handle_alertness_callback()`**:

Two-phase callback handling:
1. **Number Selection**: User clicks 1-10 → Save selection, rebuild question with Submit button
2. **Submit**: User clicks Submit → Validate all data, save to database, show summary

This prevents accidental submission and gives users confidence they selected the right rating.

## Testing

Created manual test suite (`test_alertness_fix.py`) covering:
- ✅ Submit button appears after selection (not before)
- ✅ Callback data patterns are correct
- ✅ Required field validation works
- ✅ Missing field detection works
- ✅ Sleep duration calculation is correct

**All tests pass.**

## Code Quality Improvements

1. **Better UX**:
   - Clear instructions at each step
   - Visual feedback (shows selection)
   - Prevents accidental submission
   - Consistent with Q7 pattern

2. **Robustness**:
   - Comprehensive error handling
   - Data validation before processing
   - Graceful failure modes
   - Detailed error logging

3. **Maintainability**:
   - Clear code comments
   - Structured error handling
   - Testable logic

## Impact

**Before**:
- Users confused about how to complete quiz
- Silent failures with no feedback
- No way to recover from errors
- Lost sleep tracking data

**After**:
- Clear, intuitive completion flow
- Helpful error messages
- Automatic cleanup on errors
- Reliable data capture

## Files Modified

- `src/handlers/sleep_quiz.py` (lines 415-596)

## Files Created

- `RCA-sleep-quiz-stuck-on-question-8.md` - Detailed root cause analysis
- `test_alertness_fix.py` - Manual test suite
- `BUG_FIX_SUMMARY.md` - This document

## Related Issues

The original issue (#4) also contained feature requests:
- Multi-language support
- Default activation with opt-out
- Customizable quiz timing
- Telegram sensor integration

These are **separate features** and have been moved to a new issue (to be created).

## Deployment Notes

No database migrations required.
No breaking changes to existing functionality.
Safe to deploy immediately.

## Verification Steps

1. Start sleep quiz: `/sleep_quiz`
2. Answer questions 1-7 normally
3. On Q8:
   - Verify numbers 1-10 are shown
   - Verify NO submit button initially
   - Click a number (e.g., 7)
   - Verify "Selected: 7/10" appears
   - Verify "✅ Submit" button appears
   - Click different number → verify selection updates
   - Click Submit → verify quiz completes
   - Verify summary shows all data correctly

## Success Criteria

- ✅ Users can complete the quiz without confusion
- ✅ Clear visual feedback at each step
- ✅ Errors are caught and reported gracefully
- ✅ Quiz data is validated before saving
- ✅ All existing tests still pass

---

**Fixed by**: Remote Coding Agent
**Date**: 2025-12-19
**Related Issue**: #4 (Sleep-quiz check and language)
