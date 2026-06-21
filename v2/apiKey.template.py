# API key template.
#
# Copy this file to `apiKey.py` (same v2/ directory) and paste in your own keys:
#
#     cp v2/apiKey.template.py v2/apiKey.py
#     # then edit v2/apiKey.py
#
# `v2/apiKey.py` is git-ignored, so your real keys are never committed.
#
#   OpenAI key:  https://platform.openai.com/api-keys
#   Gemini key:  https://aistudio.google.com/app/apikey
#
# The synthesis pipeline uses OpenAI by default; the Gemini key is only needed for
# the optional Gemini code paths, but both names must be defined.

OPENAI_API_KEY = "YOUR_OPENAI_API_KEY_HERE"
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY_HERE"
