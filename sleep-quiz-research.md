# Sleep Quiz Research for 15-Year-Old Users

## Executive Summary

This document contains research findings on the best format and questions for a "how did you sleep last night" quiz designed for 15-year-old boys. The quiz should be fast to fill out, minimize typing, and maximize relevant information through buttons and sliders.

---

## Key Research Findings

### 1. Adolescent Sleep Patterns at Age 15

- **Chronotype Changes**: Research shows that teenagers experience a natural shift toward being "night owls." Chronotype becomes increasingly later from age 10 until about age 20, with peak eveningness reached at age 19-20. The turning point toward morningness occurs at 15.7 years in girls and 17.2 years in boys.
- **Sleep Quality Issues**: Studies using the Pittsburgh Sleep Quality Index (PSQI) found poor sleep quality (scores ≥5) in 82% of adolescent participants.
- **Screen Time Impact**: Teenagers who use phones around bedtime delay sleep onset by at least 30 minutes. Those who keep phones near beds (even without using them) have poorer quality sleep than those who keep phones in another room.

### 2. Validated Sleep Assessment Frameworks

Several standardized questionnaires are used in adolescent sleep research:

#### Pittsburgh Sleep Quality Index (PSQI)
- **Components**: Assesses 7 dimensions: subjective sleep quality, sleep latency, sleep duration, habitual sleep efficiency, sleep disturbances, use of sleeping medication, and daytime dysfunction
- **Validity**: Widely used and validated for adolescent populations
- **Time Frame**: Assesses sleep over a one-month interval

#### Adolescent Sleep Hygiene Scale (ASHS)
- Focuses on behavioral practices that promote good sleep quality
- Multidimensional approach covering sleep/wake timing, sleep environment, and behavioral/emotional readiness

#### Cleveland Adolescent Sleepiness Questionnaire
- Specifically designed for teen populations
- Focuses on daytime sleepiness and alertness

---

## Recommended Quiz Format

### Best UI/UX Practices for Teen Sleep Surveys

#### ✅ **Recommended Input Types**

1. **Buttons (Radio Buttons)**
   - **Best for**: Yes/no questions, multiple choice with 2-5 options
   - **Advantages**: Easy to tap on mobile, clear visual feedback, low cognitive load
   - **Use cases**: "Did you look at your phone in bed?" (Yes/No), "How would you rate your sleep quality?" (Poor/Fair/Good/Excellent)

2. **Sliders**
   - **Best for**: Continuous scales (1-10 ratings), time ranges
   - **Advantages**: Fun and interactive, visually engaging for teens
   - **Disadvantages**: Can be tricky on touchscreens, may cause more incomplete responses
   - **Best practices**: Use sparingly for key questions, ensure large touch targets
   - **Use cases**: "How tired do you feel?" (1-10 scale), "Sleep quality rating"

3. **Time Pickers**
   - **Best for**: Bedtime, wake time, sleep onset time
   - **Advantages**: No typing required, standardized format
   - **Use cases**: "When did you go to bed?", "When did you fall asleep?", "When did you wake up?"

4. **Toggle Switches**
   - **Best for**: Binary yes/no questions
   - **Advantages**: Quick, visually appealing, very mobile-friendly
   - **Use cases**: Screen time, medications, naps

#### ❌ **Avoid**

- **Text input fields**: Require typing, slower completion, higher abandonment
- **Dropdown menus**: Require extra taps, harder to see all options
- **Long sliders on mobile**: Difficult to manipulate precisely

#### General UX Guidelines

- Show progress bar to indicate completion status
- Use clear "Next" and "Previous" buttons
- Keep quiz to 8-12 questions maximum for fast completion
- Group related questions together
- Make the survey mobile-first (most teens will complete on phone)
- Avoid screens 1 hour before bed recommendation conflicts with "fill out before sleep" timing

---

## Recommended Questions for 15-Year-Old Sleep Quiz

### Core Questions (Essential - 8 questions)

1. **What time did you get into bed last night?**
   - Format: Time picker
   - Why: Establishes bedtime routine start

2. **How long did it take you to fall asleep?**
   - Format: Buttons (Less than 15 min / 15-30 min / 30-60 min / More than 1 hour)
   - Why: Measures sleep latency, a key PSQI component

3. **What time did you wake up this morning?**
   - Format: Time picker
   - Why: Calculates total sleep duration

4. **Did you wake up during the night?**
   - Format: Buttons (No / Yes, 1-2 times / Yes, 3+ times)
   - Why: Assesses sleep disturbances

5. **Did you use your phone/screen while in bed?**
   - Format: Toggle + conditional follow-up
   - Follow-up if Yes: "For how long?" (Buttons: Less than 15 min / 15-30 min / 30-60 min / More than 1 hour)
   - Why: Critical factor affecting teen sleep quality

6. **How would you rate your sleep quality last night?**
   - Format: Slider (1-10 scale with emoji indicators)
   - Labels: 1 = Terrible 😫, 5 = Okay 😐, 10 = Excellent 😊
   - Why: Subjective sleep quality assessment

7. **How tired/alert do you feel right now?**
   - Format: Slider (1-10 scale)
   - Labels: 1 = Exhausted 😴, 5 = Normal 😐, 10 = Wide awake ⚡
   - Why: Measures daytime dysfunction, correlates with sleep quality

8. **Did anything disrupt your sleep?** (Select all that apply)
   - Format: Multi-select buttons
   - Options: Noise / Light / Too hot/cold / Stress/worry / Nightmares / Pain/discomfort / Nothing
   - Why: Identifies specific sleep disturbances

### Enhanced Questions (Optional - Add 3-5 for more detail)

9. **Did you exercise yesterday?**
   - Format: Buttons (No / Light activity / Moderate / Intense workout)
   - Why: Physical activity affects sleep quality

10. **Did you consume any of these before bed?**
    - Format: Multi-select buttons
    - Options: Caffeine / Large meal / Sugary snacks / Energy drinks / None
    - Why: Diet impacts sleep onset and quality

11. **Did you take a nap yesterday?**
    - Format: Toggle + conditional
    - Follow-up if Yes: "How long?" (Buttons: Less than 30 min / 30-60 min / 1-2 hours / More than 2 hours)
    - Why: Naps affect nighttime sleep patterns

12. **How stressful was your day yesterday?**
    - Format: Slider (1-10 scale)
    - Labels: 1 = Very relaxed, 10 = Extremely stressed
    - Why: Stress correlates with poor sleep quality

13. **Where did you sleep?**
    - Format: Buttons (My bed / Someone else's bed / Couch/other)
    - Why: Sleep environment affects quality

---

## Question Grouping & Flow

### Recommended Structure:

**Section 1: Sleep Timing (3 questions)**
- What time did you get into bed?
- How long did it take to fall asleep?
- What time did you wake up?

**Section 2: Sleep Quality (3 questions)**
- Did you wake up during the night?
- How would you rate your sleep quality?
- Did anything disrupt your sleep?

**Section 3: Pre-Sleep Behavior (1-2 questions)**
- Did you use your phone/screen while in bed?
- [Optional] Did you consume caffeine/food before bed?

**Section 4: Current State (1 question)**
- How tired/alert do you feel right now?

**Total completion time**: 60-90 seconds

---

## Data Collection & Insights

### Key Metrics to Calculate

1. **Total Sleep Duration**: Wake time - Bedtime - Sleep latency
2. **Sleep Efficiency**: (Total sleep time / Time in bed) × 100
3. **Sleep Latency**: Time to fall asleep
4. **Sleep Disturbance Score**: Frequency of night wakings + disruption factors
5. **Screen Time Impact**: Correlation between screen use and sleep quality
6. **Daytime Dysfunction**: Morning alertness rating

### Clinically Relevant Thresholds (for 15-year-olds)

- **Recommended sleep duration**: 8-10 hours per night
- **Concerning sleep latency**: >30 minutes regularly
- **Screen time cutoff**: Should stop 1 hour before bed (30 minutes minimum)
- **Poor sleep quality threshold**: PSQI score ≥5 indicates poor sleep

### Patterns to Track Over Time

- Weekday vs. weekend sleep patterns
- Screen time correlation with sleep quality
- Consistency of bedtime/wake time
- Sleep debt accumulation during school week

---

## Implementation Recommendations

### Mobile-First Design
- Large touch targets (minimum 44x44 pixels)
- Thumb-friendly placement of buttons
- Swipe gestures for navigation
- Dark mode option (ironic but appreciated by teens)

### Engagement Features
- Progress indicator showing "2 of 8 questions"
- Quick completion badge: "Done in 60 seconds!"
- Visual feedback with emoji reactions
- Optional: Streak tracking for daily completion
- Optional: Simple data visualization of their sleep patterns

### Accessibility
- High contrast colors
- Large, readable fonts (minimum 16px)
- Screen reader compatible
- Works without internet (save and sync later)

### Privacy Considerations
- Clear data usage explanation
- Option to keep data private
- No identifying information required
- Anonymous completion option

---

## Sample Question Implementation

### Example 1: Sleep Quality Slider
```
Question: "How would you rate your sleep quality last night?"

[😫]----[😐]----[😊]
 1   3   5   7   9  10

Default position: 5 (middle)
Thumb-friendly slider with haptic feedback
```

### Example 2: Phone Usage
```
Question: "Did you use your phone while in bed?"

[NO]  [YES]  ← Large toggle buttons

If YES selected, slide in:
"For how long?"
[<15 min]  [15-30 min]  [30-60 min]  [1+ hour]
```

### Example 3: Sleep Disruptions
```
Question: "What disrupted your sleep?" (Select all that apply)

[🔊 Noise]  [💡 Light]  [🌡️ Temperature]
[😰 Stress]  [😱 Bad dream]  [🤕 Pain]
[✅ Nothing]

Multi-select pill buttons with icons
```

---

## Evidence Base & Validation

### Research-Backed Question Selection

All recommended questions are derived from validated instruments:
- **Sleep timing questions**: Based on PSQI sleep duration and latency components
- **Sleep quality rating**: PSQI subjective sleep quality component
- **Night wakings**: PSQI sleep disturbances component
- **Daytime alertness**: PSQI daytime dysfunction component
- **Screen time**: Multiple studies confirm strong correlation with adolescent sleep problems
- **Sleep environment factors**: Adolescent Sleep Hygiene Scale (ASHS) components

### Age-Appropriate Considerations

For 15-year-old boys specifically:
- At peak of chronotype shift toward eveningness (natural "night owl" tendency)
- High likelihood of phone/screen use in bed (nearly universal in this demographic)
- School start times often conflict with natural sleep patterns
- Social media use is a significant factor in delayed sleep onset
- May underreport sleep problems or not recognize symptoms

---

## Sources

### Adolescent Sleep Assessment
- [Development and field test of the child and adolescent sleep checklist](https://www.frontiersin.org/journals/child-and-adolescent-psychiatry/articles/10.3389/frcha.2025.1644128/pdf)
- [Technology Use and Sleep Quality in Preadolescence](https://jcsm.aasm.org/doi/pdf/10.5664/jcsm.5282)
- [Adolescent sleep hygiene scale questionnaire - JCDR](https://www.jcdr.net/article_fulltext.asp?issn=0973-709x&year=2022&month=October&volume=16&issue=10&page=SC01&id=16997)
- [Subjective Sleep Measures in Children: Self-Report - Frontiers](https://www.frontiersin.org/journals/pediatrics/articles/10.3389/fped.2017.00022/full)
- [Cleveland Adolescent Sleepiness Questionnaire](https://sleepeducation.org/wp-content/uploads/2021/04/teen-sleep-questionnaire.pdf)

### Pittsburgh Sleep Quality Index (PSQI)
- [The Pittsburgh Sleep Quality Index (PSQI) - CSCS](https://www.sleep.pitt.edu/psqi)
- [PSQI validity and factor structure in young people - PubMed](https://pubmed.ncbi.nlm.nih.gov/26653055/)
- [PSQI and Associated Factors in Middle-school Students - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC8650888/)
- [Sleep Quality in Adolescents - Journal of Pediatric Research](https://jpedres.org/articles/sleep-quality-in-adolescents-in-relation-to-age-and-sleep-related-habitual-and-environmental-factors/doi/jpr.galenos.2019.86619)

### Survey UX and Design
- [How to Use a Slider Scale in Surveys - SurveySparrow](https://surveysparrow.com/blog/slider-scale/)
- [Designing surveys: ultimate tips and examples - Justinmind](https://www.justinmind.com/ui-design/surveys-examples-questions)
- [Understanding and Utilizing Survey Slider Questions - Alchemer](https://www.alchemer.com/resources/blog/slider-questions-are-here/)
- [Evidence-Based Survey Design: The Use of Sliders - TD](https://www.td.org/content/atd-blog/evidence-based-survey-design-the-use-of-sliders)
- [Sliders versus Numeric Scales on Desktop and Mobile - MeasuringU](https://measuringu.com/uxlite-numeric-slider-desktop-mobile/)

### Chronotype Research
- [From Lark to Owl: developmental changes - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC5381104/)
- [Chronotypes: Definition, Types, & Effect on Sleep - Sleep Foundation](https://www.sleepfoundation.org/how-sleep-works/chronotypes)
- [Morningness Eveningness Questionnaire Guide - Number Analytics](https://www.numberanalytics.com/blog/morningness-eveningness-questionnaire-guide)

### Screen Time and Adolescent Sleep
- [Youth screen media habits and sleep - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC5839336/)
- [How Screen Time May Cause Insomnia in Teens - Sleep Foundation](https://www.sleepfoundation.org/teens-and-sleep/screen-time-and-insomnia-for-teens)
- [Adolescent Sleep and Technology Use Before Sleep - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC5026973/)
- [Teens and phones in bed affect sleep - The Conversation](https://theconversation.com/its-almost-impossible-to-keep-teens-off-their-phones-in-bed-but-new-research-shows-it-really-does-affect-their-sleep-237955)
- [Screen time affecting teen sleep and mental health - World Economic Forum](https://www.weforum.org/stories/2023/09/screen-time-affecting-sleep-mental-health/)

---

## Conclusion

The optimal sleep quiz for a 15-year-old boy should:

1. **Be fast**: 8-10 core questions, 60-90 seconds to complete
2. **Minimize typing**: Use time pickers, buttons, toggles, and sliders
3. **Be mobile-optimized**: Large touch targets, thumb-friendly layout
4. **Focus on key metrics**: Sleep timing, quality, screen time, and daytime alertness
5. **Use validated questions**: Based on PSQI, ASHS, and other research-backed instruments
6. **Be engaging**: Visual feedback, progress indicators, emoji reactions
7. **Provide value**: Give insights about sleep patterns and recommendations

The most critical questions to include are:
- Bedtime, sleep latency, and wake time (calculate sleep duration)
- Subjective sleep quality rating
- Screen/phone use in bed
- Night wakings
- Morning alertness/tiredness

This combination provides maximum clinical insight with minimum user burden, perfectly suited for daily tracking in a 15-year-old population.
