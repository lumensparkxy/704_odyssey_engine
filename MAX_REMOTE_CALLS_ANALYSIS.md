# Google Search Grounding: MAX_REMOTE_CALLS Analysis

## Question
Is the "AFC is enabled with max remote calls: 10" value configurable or hardcoded?

## Investigation Results

### Source of the Message
- **Origin**: The message comes from the `google-generativeai` library, not from the Odyssey Engine code
- **Context**: Appears when using Google Search grounding with `Tool(google_search=GoogleSearch())`
- **AFC**: Stands for "Automatic Function Calling" - an internal library feature

### Configurability Analysis

#### ❌ NOT Configurable via API
The `max_remote_calls` parameter is **hardcoded to 10** in the Google Generative AI library and cannot be configured from the client side.

**Evidence:**
```python
# This fails with "Extra inputs are not permitted"
GoogleSearch(max_remote_calls=5)  # ❌ Error

# Only this works:
GoogleSearch()  # ✅ Uses default 10
```

**Error Message:**
```
1 validation error for GoogleSearch
max_remote_calls
  Extra inputs are not permitted [type=extra_forbidden, input_value=5, input_type=int]
```

### Impact and Recommendations

#### Cost Implications
- Each Google Search grounding request can make up to **10 remote calls** to Google Search
- This is a fixed cost that cannot be reduced through configuration
- Users should be aware of this when using grounding extensively

#### Alternative Approaches
1. **Limit grounding usage**: Use `enable_search=False` for some queries
2. **Cache results**: Implement caching to reduce repeated searches
3. **Smart grounding**: Only enable grounding for queries that truly need it

#### Configuration Updates Made
1. **Documentation**: Added comments explaining the limitation
2. **Settings Display**: Shows "(not configurable)" next to the setting
3. **Environment Variables**: Kept `MAX_REMOTE_CALLS=10` for documentation
4. **Removed Failed Configuration**: Removed the attempt to configure `GoogleSearch(max_remote_calls=...)`

### Current Implementation
```python
# In GeminiClient.generate_with_grounding():
config = GenerateContentConfig(
    tools=[Tool(google_search=GoogleSearch())],  # Always uses default 10
    temperature=0.5,
    max_output_tokens=8192,
    safety_settings=self.safety_settings
)
```

### Conclusion
The "10" in "AFC is enabled with max remote calls: 10" is a **fixed value** that cannot be changed through the API. This is an internal limitation of the Google Generative AI library. The Odyssey Engine configuration has been updated to document this limitation clearly.

### Monitoring Usage
To monitor actual Google Search usage:
1. Check the logs for "AFC is enabled with max remote calls: 10" frequency
2. Monitor API costs in Google Cloud Console
3. Consider implementing usage tracking in the application

---

**Status**: ✅ Analyzed and documented  
**Date**: July 6, 2025  
**Library Version**: google-generativeai (latest)
