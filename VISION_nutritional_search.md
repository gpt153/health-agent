# Vision: Enhanced Nutritional Data Accuracy via Online Search

## Problem Statement

Currently, the health agent relies solely on Vision AI (GPT-4o-mini or Claude 3.5 Sonnet) to estimate nutritional data from food photos. While convenient, these estimates:

- Lack authoritative backing (users may not trust AI estimates)
- Cannot provide precise data for specific brands or products
- Miss comprehensive micronutrient information (vitamins, minerals, fiber, sodium)
- May be inaccurate for uncommon foods or regional products

## Vision

Enable the health agent to verify and enhance nutritional data by searching authoritative, free-tier nutritional databases after Vision AI identifies foods. This hybrid approach combines visual food identification with verified nutritional data, significantly improving accuracy and user trust.

## Goals

### Primary Goals
1. **Improve accuracy**: Replace AI estimates with verified data from USDA and Open Food Facts
2. **Increase user trust**: Show data source (USDA, Open Food Facts, or AI estimate)
3. **Stay free**: Use only free-tier APIs with no cost
4. **Seamless UX**: Automatic verification without user intervention

### Secondary Goals
1. **Comprehensive data**: Include micronutrients (fiber, vitamins, sodium) beyond just macros
2. **International support**: Support non-US foods via Open Food Facts
3. **Brand awareness**: Match specific branded products when possible
4. **Transparency**: Clearly indicate data source and confidence level

## Success Criteria

- ✅ 80%+ of identified foods are successfully verified against databases
- ✅ Nutritional data accuracy improves by measurable margin
- ✅ User feedback indicates increased trust in nutritional data
- ✅ Response time remains under 5 seconds for photo analysis + verification
- ✅ Zero API cost (all within free tiers)

## Non-Goals (Out of Scope)

- ❌ Barcode scanning (future enhancement)
- ❌ Recipe analysis with ingredient breakdown (future enhancement)
- ❌ Restaurant menu integration beyond basic search (future enhancement)
- ❌ Custom food database for user-created foods (future enhancement)
- ❌ Meal planning or recommendations (separate feature)

## Proposed Solution

### Architecture: Hybrid Verification System

```
User uploads food photo + caption
         ↓
Vision AI analyzes photo
  - Identifies foods visually
  - Provides initial estimates
         ↓
For each identified food:
  1. Normalize food name (e.g., "grilled chicken" → "chicken breast, grilled")
  2. Search USDA FoodData Central (whole foods)
  3. If not found → Search Open Food Facts (packaged/branded)
  4. If found → Replace AI estimate with verified data
  5. If not found → Keep AI estimate, mark as "estimated"
         ↓
Return merged results with confidence markers
```

### Data Sources

**USDA FoodData Central**
- **Cost**: FREE (requires API key, no usage fees)
- **Rate limit**: 1,000 requests/hour per IP
- **Best for**: Whole foods (chicken, vegetables, grains, dairy)
- **Data quality**: Authoritative, government-verified
- **Coverage**: ~350,000+ foods, primarily US-based

**Open Food Facts**
- **Cost**: FREE (no API key required)
- **Rate limit**: No strict limits for reasonable use
- **Best for**: Packaged foods, branded products, international foods
- **Data quality**: Crowdsourced, varies by product
- **Coverage**: 2.3M+ products from 182 countries

### Key Features

1. **Automatic Verification**
   - After Vision AI identifies foods, automatically search databases
   - No user intervention required
   - Fallback chain: USDA → Open Food Facts → AI estimate

2. **Confidence Indicators**
   - `✅ Verified (USDA)` - Data from USDA database
   - `✅ Verified (Open Food Facts)` - Data from crowdsourced database
   - `⚠️ Estimated` - AI estimate only (no database match)

3. **Enhanced Nutritional Data**
   - Macros: protein, carbs, fat (current)
   - Micronutrients: fiber, sodium, vitamins, minerals (new)
   - Serving sizes: standardized USDA portions

4. **Smart Food Name Matching**
   - Normalize food names for better search results
   - Handle common variations ("chicken breast" vs "breast, chicken")
   - Support multilingual input (Swedish → English translation)

### User Experience

**Before (current):**
```
📸 I see:
• Grilled chicken breast, 150g - 248 cal
  Protein: 46g | Carbs: 0g | Fat: 5g
```

**After (with verification):**
```
📸 I see:
• Grilled chicken breast, 150g - 248 cal ✅ Verified (USDA)
  Protein: 46.5g | Carbs: 0g | Fat: 5.4g
  Fiber: 0g | Sodium: 89mg

• Broccoli, 1 cup - 55 cal ✅ Verified (USDA)
  Protein: 4.3g | Carbs: 11g | Fat: 0.6g
  Fiber: 5.1g | Vitamin C: 135% DV
```

## Technical Implementation

### New Components

**1. Nutrition Search Utility (`src/utils/nutrition_search.py`)**
- `search_usda(food_name: str, quantity: str) → Optional[NutritionData]`
- `search_openfoodfacts(food_name: str) → Optional[NutritionData]`
- `verify_nutrition(food_items: list[FoodItem]) → list[FoodItem]`
- Handle API calls, result parsing, caching, error handling

**2. Enhanced Data Models**
- Add `verification_source: Optional[str]` to `FoodItem` model
  - Values: "usda", "openfoodfacts", "ai_estimate", None
- Add `micronutrients: Optional[Micronutrients]` to `FoodMacros`
  - Fields: fiber, sodium, sugar, vitamins, minerals

**3. Updated Vision Integration**
- Modify `src/utils/vision.py` after Vision AI returns results
- Call `verify_nutrition()` to enhance with database data
- Merge verified data while preserving visual identification

**4. Configuration**
- Add `USDA_API_KEY` environment variable (free signup)
- Add `ENABLE_NUTRITION_VERIFICATION=true` feature flag
- Add `NUTRITION_CACHE_TTL=3600` (cache results for 1 hour)

### API Integration Details

**USDA FoodData Central API**
- Endpoint: `https://api.nal.usda.gov/fdc/v1/foods/search`
- Auth: API key in query param (`?api_key=...`)
- Search params: `query`, `pageSize`, `dataType`
- Response: JSON with nutrient details per 100g

**Open Food Facts API**
- Endpoint: `https://world.openfoodfacts.org/cgi/search.pl`
- Auth: None required
- Search params: `search_terms`, `search_simple=1`, `json=1`
- Response: JSON with product details, nutrients per 100g

### Dependencies

**New:**
- `httpx` or `aiohttp` - Async HTTP client for API calls
- May already be installed or add to `requirements.txt`

**Existing:**
- `pydantic` - Data validation (already installed)
- `python-dotenv` - Environment variables (already installed)

### File Changes

**New files:**
- `src/utils/nutrition_search.py` - API integration
- `tests/unit/test_nutrition_search.py` - Unit tests
- `tests/integration/test_nutrition_verification.py` - Integration tests
- `.env.example` - Add USDA_API_KEY documentation

**Modified files:**
- `src/utils/vision.py` - Add verification step
- `src/models/food.py` - Add verification_source, micronutrients
- `requirements.txt` - Add httpx if needed
- `src/config.py` - Add USDA_API_KEY, feature flags

## Implementation Phases

### Phase 1: Foundation (MVP)
- Set up USDA API integration
- Create basic verification for whole foods
- Add verification_source to data model
- Test with common foods (chicken, rice, broccoli)

### Phase 2: Enhancement
- Add Open Food Facts for packaged foods
- Implement smart food name matching
- Add micronutrient support
- Cache frequently searched foods

### Phase 3: Polish
- Optimize search accuracy with better matching
- Add comprehensive tests
- Performance optimization (parallel searches)
- User feedback collection

## Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| API rate limits exceeded | High | Implement caching, respect rate limits, fallback to AI |
| Poor search match accuracy | Medium | Normalize names, fuzzy matching, manual verification hints |
| API downtime | Medium | Graceful degradation to AI estimates, retry logic |
| Slow response times | Medium | Parallel API calls, caching, timeout handling |
| Data quality (Open Food Facts) | Low | Prefer USDA, show confidence indicators |

## Metrics & Monitoring

**Key Metrics:**
- Verification success rate (% of foods matched)
- API response time (p50, p95, p99)
- Cache hit rate
- User satisfaction (via feedback)
- API error rate

**Monitoring:**
- Log all API calls and responses
- Track verification success/failure by food type
- Monitor rate limit proximity
- Alert on API errors > 5%

## Future Enhancements (Post-MVP)

1. **Barcode Scanning**: Use phone camera to scan product barcodes
2. **Recipe Analysis**: Break down recipes into ingredient-level nutrition
3. **Restaurant Menus**: Integrate restaurant nutritional databases
4. **Custom Foods**: Allow users to add their own foods to personal database
5. **Offline Mode**: Download USDA database for offline lookup
6. **Meal Suggestions**: Recommend foods based on nutritional goals

## Success Indicators

**Week 1:**
- USDA integration working for 10+ common foods
- Verification success rate > 60%

**Week 2:**
- Open Food Facts integrated
- Verification success rate > 75%
- Response time < 5 seconds

**Week 4:**
- Verification success rate > 85%
- User feedback indicates improved trust
- Zero critical bugs

## Open Questions

1. **Search specificity**: How strict should food name matching be? (exact vs fuzzy)
2. **Quantity normalization**: How to handle "1 cup" vs "100g" conversions?
3. **Multiple matches**: Show user multiple options or auto-select best match?
4. **Micronutrient display**: Show all micronutrients or only key ones?
5. **Caching strategy**: Cache by food name only or include quantity?

## Appendix: API Examples

### USDA FoodData Central Search

**Request:**
```bash
GET https://api.nal.usda.gov/fdc/v1/foods/search?query=chicken%20breast&api_key=YOUR_KEY
```

**Response (simplified):**
```json
{
  "foods": [{
    "description": "Chicken, broilers or fryers, breast, meat only, cooked, roasted",
    "foodNutrients": [
      {"nutrientName": "Protein", "value": 31.02, "unitName": "g"},
      {"nutrientName": "Total lipid (fat)", "value": 3.57, "unitName": "g"},
      {"nutrientName": "Carbohydrate", "value": 0, "unitName": "g"},
      {"nutrientName": "Energy", "value": 165, "unitName": "kcal"}
    ]
  }]
}
```

### Open Food Facts Search

**Request:**
```bash
GET https://world.openfoodfacts.org/cgi/search.pl?search_terms=greek%20yogurt&json=1
```

**Response (simplified):**
```json
{
  "products": [{
    "product_name": "Greek Yogurt",
    "brands": "Fage",
    "nutriments": {
      "energy-kcal_100g": 97,
      "proteins_100g": 10.2,
      "carbohydrates_100g": 3.6,
      "fat_100g": 4.8
    }
  }]
}
```

## References

- [USDA FoodData Central API Guide](https://fdc.nal.usda.gov/api-guide/)
- [USDA API Key Signup](https://fdc.nal.usda.gov/api-key-signup/)
- [Open Food Facts API Documentation](https://openfoodfacts.github.io/openfoodfacts-server/api/)
- [Open Food Facts Data](https://world.openfoodfacts.org/data)
