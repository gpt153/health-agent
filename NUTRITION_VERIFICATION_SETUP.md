# USDA Nutrition Verification Setup

## Overview

Phase 1 of the nutritional data verification system has been implemented. This integrates the USDA FoodData Central API to verify and enhance nutrition data from AI vision analysis.

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

The new dependency added: `httpx>=0.27.0`

### 2. Get USDA API Key

1. Visit https://fdc.nal.usda.gov/api-key-signup.html
2. Sign up for a free API key
3. You'll receive the key via email

### 3. Configure Environment

Copy `.env.example` to `.env` and update:

```bash
cp .env.example .env
```

Edit `.env` and set:

```
USDA_API_KEY=your_actual_api_key_here
ENABLE_NUTRITION_VERIFICATION=true
```

**Note:** The system defaults to `ENABLE_NUTRITION_VERIFICATION=true`, so verification will be enabled by default.

### 4. Rate Limits

- USDA API allows 1,000 requests per hour with a free API key
- The implementation includes a 24-hour in-memory cache to minimize API calls
- Timeout is set to 5 seconds per request

## How It Works

### Verification Flow

1. **Vision AI Analysis**: User sends a food photo, Vision AI identifies foods
2. **USDA Verification**: Each food item is verified against USDA database
3. **Nutrient Scaling**: USDA nutrients are scaled to match user's quantity
4. **Enhanced Response**: User receives verified data with micronutrients

### Fallback Strategy

If USDA verification fails (no match, API error, timeout):
- System automatically falls back to original Vision AI estimates
- Item is marked with `verification_source: "ai_estimate"`
- No user-facing error - seamless experience

### Response Format

Verified items show a ✓ badge:
```
• Chicken Breast ✓ (170g)
  └ 280 cal | P: 52.7g | C: 0g | F: 6.1g | Fiber: 0g | Sodium: 125.8mg
```

AI estimates show a ~ badge:
```
• Mystery Food ~ (100g)
  └ 150 cal | P: 10g | C: 20g | F: 5g
```

## New Features

### 1. Micronutrients

The system now tracks:
- Fiber (grams)
- Sodium (milligrams)
- Sugar (grams)
- Vitamin C (milligrams)
- Calcium (milligrams)
- Iron (milligrams)

### 2. Verification Metadata

Each food item includes:
- `verification_source`: "usda" or "ai_estimate"
- `confidence_score`: 0.0-1.0 (based on USDA match score)

### 3. Backward Compatibility

All existing data continues to work:
- Old FoodItem objects work without modification
- New fields are optional (default to None)
- No database migration required

## Testing

### Run Unit Tests

```bash
pytest tests/unit/test_nutrition_search.py -v
```

### Test Coverage

- Normalization of food names
- Quantity parsing (grams, cups, items, etc.)
- USDA API search with caching
- Nutrient scaling with unit conversion
- End-to-end verification flow
- Error handling and fallbacks
- Multiple food items
- Backward compatibility

### Manual Testing

1. Send a food photo with caption: "170g chicken breast"
2. Check for ✓ badge in response
3. Verify micronutrients (fiber, sodium) are shown
4. Check logs for USDA API calls

## File Structure

```
src/
├── config.py                    # Added USDA_API_KEY, ENABLE_NUTRITION_VERIFICATION
├── models/
│   └── food.py                 # Added Micronutrients, updated FoodMacros & FoodItem
├── utils/
│   └── nutrition_search.py     # NEW: USDA API client (310 lines)
└── bot.py                      # Modified photo handler to use verification

tests/
└── unit/
    └── test_nutrition_search.py # NEW: Comprehensive tests (428 lines)

requirements.txt                 # Added httpx>=0.27.0
.env.example                    # Added USDA configuration
```

## Monitoring and Debugging

### Logging

All USDA API calls are logged:
```
INFO - Searching USDA for 'chicken breast'
INFO - USDA search returned 100 results
INFO - USDA match: 'Chicken, broilers or fryers, breast, meat only, cooked, roasted' (score: 800)
INFO - Verified 'Chicken Breast': 280 cal (USDA)
```

### Cache Monitoring

Check cache hits:
```
INFO - Cache hit for 'chicken breast'
```

### Error Tracking

All errors are logged with fallback to AI estimates:
```
WARNING - USDA API timeout for 'mystery food'
INFO - No USDA match for 'Mystery Food', using AI estimate
```

## Limitations (Phase 1)

- In-memory cache (cleared on restart)
- No batch API calls (sequential requests)
- Basic name normalization (no fuzzy matching)
- USDA-only (no other databases)
- English names only

## Next Steps (Future Phases)

- Phase 2: Multi-source verification (USDA + Nutritionix + Open Food Facts)
- Phase 3: Redis caching for persistence
- Phase 4: Batch processing and performance optimization
- Phase 5: Admin dashboard for verification monitoring

## Troubleshooting

### Issue: No verification happening

**Check:**
1. `ENABLE_NUTRITION_VERIFICATION=true` in `.env`
2. Valid USDA API key in `.env`
3. Network connectivity to api.nal.usda.gov
4. Check logs for error messages

### Issue: Rate limit errors

**Solution:**
- Cache should prevent most duplicate calls
- Consider upgrading USDA API plan
- Or reduce `max_results` in `search_usda()`

### Issue: Poor matches

**Solution:**
- Name normalization may need tuning
- Check food name in logs
- Future: implement fuzzy matching

## API Reference

### `verify_food_items(food_items: List[FoodItem]) -> List[FoodItem]`

Main entry point for verification.

**Parameters:**
- `food_items`: List of FoodItem from Vision AI

**Returns:**
- List of FoodItem with verified/enhanced data

**Behavior:**
- Calls USDA API for each item
- Scales nutrients to target quantity
- Falls back to AI estimate on error
- Adds verification metadata

### `search_usda(food_name: str, max_results: int = 3) -> Optional[Dict]`

Search USDA FoodData Central.

**Parameters:**
- `food_name`: Normalized food name
- `max_results`: Max results to return (default: 3)

**Returns:**
- USDA API response dict or None if failed

**Features:**
- 24-hour cache
- 5-second timeout
- Comprehensive error handling

### `normalize_food_name(name: str) -> str`

Normalize food names for better matching.

**Removes:**
- Cooking methods (grilled, baked, fried)
- Size qualifiers (large, medium, small)
- Quality markers (organic, fresh, raw)

### `parse_quantity(quantity_str: str) -> Tuple[float, str]`

Parse quantity strings.

**Supported units:**
- Grams: "100g", "100 grams"
- Ounces: "4oz"
- Pounds: "1lb"
- Kilograms: "0.5kg"
- Cups: "1 cup", "2 cups"
- Tablespoons: "2 tbsp"
- Teaspoons: "1 tsp"
- Items: "2 eggs", "1 apple"

**Returns:**
- `(amount, unit)` tuple

### `scale_nutrients(usda_food: Dict, target_amount: float, target_unit: str) -> Optional[Dict]`

Scale USDA nutrients to target quantity.

**Handles:**
- Unit conversion (oz to g, lb to g, etc.)
- Portion scaling
- Nutrient extraction

**Returns:**
- Dict with scaled nutrient values or None

## Support

For issues or questions, check:
1. This documentation
2. Code comments in `src/utils/nutrition_search.py`
3. Test cases in `tests/unit/test_nutrition_search.py`
4. USDA API docs: https://fdc.nal.usda.gov/api-guide.html
