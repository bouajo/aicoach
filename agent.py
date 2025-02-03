"""
agent.py
Core conversation logic for AI Diet Coach.

Process:
1) If user doesn't exist -> create them, send welcome message
2) Next message: detect language, store it
3) Ask for start_weight, then target_weight
4) Summarize, ask for confirmation
5) If user confirms -> move to 'chat' state
6) Chat normally (but for now we just do a simple response or a placeholder)
"""

import logging
import re
import json
from typing import Tuple, Optional, Dict, Any, List
from datetime import datetime
from database import db
from deepseek import detect_language, chat_completion

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Language settings
DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = {
    "en": "English",
    "fr": "Français",
    "es": "Español",
    "ar": "العربية",
    "hi": "हिंदी",
    "zh": "中文",
    "ja": "日本語",
    "ko": "한국어"
}

async def generate_welcome_message() -> str:
    """Generate a dynamic welcome message that introduces language options."""
    system_prompt = """Generate a welcoming message for a diet coach app that:
    1. Greets the user warmly
    2. Explains that the coach can communicate in any language
    3. Asks them to reply in their preferred language
    4. Lists supported languages with their emojis
    
    Format the message to be clear and welcoming.
    Include appropriate emojis for a friendly tone.
    Keep the message concise but informative."""
    
    try:
        welcome = await chat_completion(
            system_prompt=system_prompt,
            user_message="Generate a welcome message listing these languages: " + 
                        ", ".join(f"{code}: {name}" for code, name in SUPPORTED_LANGUAGES.items())
        )
        return welcome
    except Exception as e:
        logger.error(f"Error generating welcome message: {e}")
        return "👋 Welcome! Please reply in your preferred language, and I'll continue in that language."

# Initialize welcome message
WELCOME_MESSAGE = None

async def ensure_welcome_message():
    """Ensure welcome message is initialized."""
    global WELCOME_MESSAGE
    if WELCOME_MESSAGE is None:
        WELCOME_MESSAGE = await generate_welcome_message()

# Remove the hardcoded COACH_INTROS dictionary and replace with a more dynamic approach
async def get_coach_intro(lang_code: str) -> str:
    """Generate a personalized coach introduction in the specified language."""
    system_prompt = f"""You are Eric, a highly experienced diet and fitness coach.
    Create a warm, personal introduction in {lang_code} that:
    1. Start with a warm greeting
    2. Introduce yourself as Eric, a nutrition and fitness expert with 20+ years experience
    3. Share your success in helping thousands achieve their goals
    4. Emphasize your personal, step-by-step guidance approach
    5. End by clearly asking for their name
    
    The tone should be:
    - Warm and welcoming
    - Professional yet approachable
    - Encouraging and positive
    - Natural and conversational
    
    IMPORTANT: 
    - Generate the response ONLY in {lang_code}
    - Keep the total message under 600 characters to fit WhatsApp limits
    - Make sure the name request is clear and complete
    - Do not include translations
    
    Format the response with appropriate spacing between paragraphs for readability."""

    try:
        intro = await chat_completion(
            system_prompt=system_prompt,
            user_message=f"Generate a concise personalized coach introduction in {lang_code} that ends with asking for their name"
        )
        
        logger.info(f"Generated coach intro in {lang_code}")
        return intro
    except Exception as e:
        logger.error(f"Error generating coach intro: {e}")
        # Generate a basic introduction as fallback
        return f"Hello! I'm Eric, your personal diet and fitness coach with over 20 years of experience. To start our journey together, could you please tell me what you'd like me to call you? 😊"

# Enhanced profile fields with dynamic question generation
PROFILE_FIELDS = {
    "language": {
        "required": True,
        "type": "language",
        "context": {
            "purpose": "Language preference for communication",
            "importance": "Ensures clear and comfortable communication",
            "cultural_context": "Respects linguistic and cultural preferences"
        }
    },
    "name": {
        "required": True,
        "type": "text",
        "context": {
            "purpose": "Personal identification",
            "importance": "Creates a personal connection",
            "cultural_context": "Used for appropriate form of address"
        }
    },
    "age": {
        "required": True,
        "type": "number",
        "context": {
            "purpose": "Age-appropriate recommendations",
            "importance": "Affects metabolism and exercise capacity",
            "medical_context": "Influences nutritional needs",
            "extract_hints": ["years old", "yo", "years", "aged", "I am", "I'm"]
        }
    },
    "gender": {
        "required": True,
        "type": "text",
        "context": {
            "purpose": "Personalized health recommendations",
            "importance": "Affects nutritional needs and body composition",
            "sensitivity": "Optional, respects privacy preferences",
            "cultural_context": "Considers cultural norms"
        }
    },
    "height": {
        "required": True,
        "type": "measurement",
        "context": {
            "purpose": "Body composition calculations",
            "importance": "Essential for BMI and health metrics",
            "flexibility": "Accepts various measurement units",
            "extract_hints": ["tall", "height", "cm", "feet", "ft", "inches", "'", "\""]
        }
    },
    "start_weight": {
        "required": True,
        "type": "weight",
        "context": {
            "purpose": "Current status assessment",
            "importance": "Baseline for progress tracking",
            "sensitivity": "Handled with care and privacy",
            "flexibility": "Accepts various weight units",
            "extract_hints": ["weigh", "kg", "lbs", "pounds", "kilos"]
        }
    },
    "target_weight": {
        "required": True,
        "type": "weight",
        "context": {
            "purpose": "Goal setting",
            "importance": "Determines program direction",
            "health_context": "Must be realistic and healthy",
            "motivation": "Personal achievement target"
        }
    },
    "goal_timeline_weeks": {
        "required": True,
        "type": "number",
        "context": {
            "purpose": "Progress planning",
            "importance": "Affects daily targets and strategies",
            "health_context": "Ensures safe weight change rate",
            "flexibility": "Accepts various time formats",
            "extract_hints": ["weeks", "months", "years", "by", "within", "around"]
        }
    },
    "activity_level": {
        "required": True,
        "type": "text",
        "context": {
            "purpose": "Energy expenditure assessment",
            "importance": "Crucial for caloric needs calculation",
            "lifestyle_context": "Considers daily routine and habits",
            "extract_hints": ["sedentary", "active", "exercise", "work", "job", "sports", "walk", "run"]
        }
    },
    "dietary_restrictions": {
        "required": False,
        "type": "text",
        "context": {
            "purpose": "Meal plan customization",
            "importance": "Ensures safe and appropriate food choices",
            "cultural_context": "Respects religious and cultural preferences",
            "health_context": "Addresses allergies and intolerances"
        }
    },
    "health_conditions": {
        "required": False,
        "type": "text",
        "context": {
            "purpose": "Safety and adaptation",
            "importance": "Ensures program safety",
            "medical_context": "Influences exercise and diet recommendations",
            "privacy": "Handled with strict confidentiality"
        }
    },
    "preferred_meals": {
        "required": False,
        "type": "number",
        "context": {
            "purpose": "Meal planning structure",
            "importance": "Matches eating habits and schedule",
            "lifestyle_context": "Accommodates daily routine",
            "extract_hints": ["meals", "eat", "times", "per day", "snacks"]
        }
    },
    "sleep_hours": {
        "required": False,
        "type": "number",
        "context": {
            "purpose": "Lifestyle assessment",
            "importance": "Affects metabolism and recovery",
            "health_context": "Influences eating patterns",
            "extract_hints": ["sleep", "hours", "night", "bed", "rest"]
        }
    },
    "stress_level": {
        "required": False,
        "type": "text",
        "context": {
            "purpose": "Lifestyle factor assessment",
            "importance": "Affects eating habits and progress",
            "health_context": "Influences program adaptations",
            "extract_hints": ["stress", "anxiety", "relaxed", "busy", "overwhelmed"]
        }
    }
}

async def log_user_interaction(phone_number: str, interaction_type: str, data: Dict[str, Any]) -> None:
    """Log user interactions in a structured way."""
    try:
        logger.info(
            "User Interaction | Phone: %s | Type: %s | Data: %s",
            phone_number[-4:],  # Only last 4 digits for privacy
            interaction_type,
            json.dumps(data, indent=2)
        )
    except Exception as e:
        logger.error(f"Error logging interaction: {e}")

async def extract_measurement(text: str, measurement_type: str, lang_code: str = "en", context: str = "") -> Dict[str, Any]:
    """Extract measurements (weight, height) from text using LLM."""
    system_prompt = f"""You are a measurement extraction expert. Extract the {measurement_type} value from user input.
    Return a JSON with:
    - value: the numeric value in standard units (kg for weight, cm for height)
    - original_unit: the unit specified by the user
    - confidence: how confident you are in the extraction (0-1)
    - context: any additional context provided
    
    Examples for weight:
    "I weigh 150 pounds" -> {{"value": 68.04, "original_unit": "pounds", "confidence": 1.0, "context": ""}}
    "75 kg" -> {{"value": 75.0, "original_unit": "kg", "confidence": 1.0, "context": ""}}
    
    Examples for height:
    "5 feet 8 inches" -> {{"value": 172.72, "original_unit": "feet_inches", "confidence": 1.0, "context": ""}}
    "170cm" -> {{"value": 170.0, "original_unit": "cm", "confidence": 1.0, "context": ""}}
    """
    
    try:
        response = await chat_completion(
            system_prompt=system_prompt,
            user_message=text
        )
        
        result = json.loads(response)
        logger.info(f"{measurement_type.title()} Extraction | Input: {text} | Result: {json.dumps(result, indent=2)}")
        return result
    except Exception as e:
        logger.error(f"Error extracting {measurement_type}: {e}")
        return {"value": None, "original_unit": "unknown", "confidence": 0}

async def extract_field_value(field_name: str, text: str, lang_code: str = "en", user_profile: Dict = None) -> Dict[str, Any]:
    """Extract and validate field values using a two-step prompt system."""
    try:
        field_info = PROFILE_FIELDS[field_name]
        field_type = field_info["type"]
        
        logger.info(f"Extracting field: {field_name} | Type: {field_type}")
        logger.info(f"Input text: {text}")
        
        # Get the last question asked to provide context
        last_question = await db.get_last_assistant_message(user_profile["phone_number"])
        
        # Build the analyzer prompt
        system_prompt = """You are an expert data analyzer for a diet coaching app.
        Your task is to extract the {field} value from the user's response.
        
        Context:
        - Field being extracted: {field}
        - Field type: {type}
        - Language: {lang}
        - Last question asked: {question}
        
        Guidelines:
        1. Analyze both the question context and the user's response
        2. Consider cultural and linguistic nuances
        3. Extract ONLY the relevant value
        4. Convert the response to the appropriate data type
        5. Validate the extracted value
        
        Response Format:
        Return a JSON object with these exact fields:
        {{
            "value": <extracted_value>,
            "confidence": <float between 0-1>,
            "normalized": <true/false>,
            "original_format": <string>
        }}
        
        Examples:
        For name: {{"value": "John", "confidence": 1.0, "normalized": true, "original_format": "john"}}
        For age: {{"value": 35, "confidence": 1.0, "normalized": true, "original_format": "35 ans"}}
        For weight: {{"value": 75.5, "confidence": 1.0, "normalized": true, "original_format": "75,5 kg"}}
        """.format(
            field=field_name,
            type=field_type,
            lang=lang_code,
            question=last_question or "No previous question"
        )
        
        # Get the analyzer's response
        analyzer_response = await chat_completion(
            system_prompt=system_prompt,
            user_message=f"Question asked: {last_question}\nUser's response: {text}"
        )
        
        try:
            result = json.loads(analyzer_response)
            
            # Log the analysis results
            logger.info(f"Analysis Result: {json.dumps(result, indent=2)}")
            
            if not result.get("value"):
                logger.error("No value extracted from analyzer")
                return None
                
            # Return only the field value for database storage
            return {field_name: result["value"]}
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse analyzer response: {e}")
            logger.error(f"Raw response: {analyzer_response}")
            return None
            
    except Exception as e:
        logger.error(f"Error in field extraction: {e}")
        return None

async def get_fallback_question(field_name: str, lang_code: str = DEFAULT_LANGUAGE) -> Tuple[str, str]:
    """Generate a fallback question when the main question generation fails."""
    system_prompt = f"""Generate a simple, polite question in {lang_code} asking for {field_name}.
    
    Consider:
    1. The field being asked for: {field_name}
    2. Cultural norms of {lang_code}
    3. Appropriate level of formality
    4. Natural phrasing in the target language
    
    The question should be:
    - Simple and clear
    - Polite and respectful
    - Natural in the target language
    - Include any necessary context for the field
    
    Return ONLY the question in {lang_code}, no translations or explanations."""
    
    try:
        question = await chat_completion(
            system_prompt=system_prompt,
            user_message=f"Generate a simple question asking for {field_name} in {lang_code}"
        )
        return field_name, question
    except Exception as e:
        logger.error(f"Error generating fallback question: {e}")
        # Ultimate fallback - should rarely be used
        return field_name, f"Please provide your {field_name}."

async def get_next_question(user_profile: dict, lang_code: str = DEFAULT_LANGUAGE) -> Tuple[str, str]:
    """Generate the next personalized question based on user profile and context."""
    # First check for missing required fields
    for field_name, field_info in PROFILE_FIELDS.items():
        if field_info["required"] and (field_name not in user_profile or user_profile[field_name] is None):
            # Skip language field as it's handled separately
            if field_name == "language":
                continue
                
            # Build a rich context for the question generation
            context = field_info.get("context", {})
            name = user_profile.get("name", "")
            
            system_prompt = f"""You are Eric, a caring and experienced diet coach having a natural conversation in {lang_code}.
            Generate a personalized question about {field_name}.
            
            Field Information:
            - Purpose: {context.get('purpose', '')}
            - Importance: {context.get('importance', '')}
            
            User Context:
            - Name: {name}
            - Language: {lang_code}
            - Current Profile: {json.dumps(user_profile, indent=2)}
            
            The question should be:
            1. Natural and conversational in {lang_code}
            2. Use their name if available
            3. Clear about what information is needed
            4. Encouraging and supportive
            5. Connected to their previous answers
            
            If asking about measurements, clarify that any unit is acceptable.
            If asking about sensitive information, emphasize that it's optional/private.
            
            IMPORTANT: Generate ONLY in {lang_code}. Do not include translations."""
            
            try:
                question = await chat_completion(
                    system_prompt=system_prompt,
                    user_message=f"Generate a friendly question about {field_name} in {lang_code}"
                )
                
                logger.info(f"Generated question for {field_name} in {lang_code}")
                return field_name, question
                
            except Exception as e:
                logger.error(f"Error generating question for {field_name}: {e}")
                # Use the fallback question generator instead of hardcoded responses
                return await get_fallback_question(field_name, lang_code)
    
    return "complete", "Profile complete"

async def get_error_message(error_type: str, lang_code: str = DEFAULT_LANGUAGE) -> str:
    """Generate an error message in the user's language."""
    system_prompt = f"""Generate an error message in {lang_code} for a diet coaching app.
    Error type: {error_type}
    
    The message should be:
    1. Clear about what went wrong
    2. Polite and understanding
    3. Provide guidance on what to do next
    4. Use appropriate tone for the language/culture
    
    Keep the message concise and helpful."""
    
    try:
        error_msg = await chat_completion(
            system_prompt=system_prompt,
            user_message=f"Generate error message for: {error_type}"
        )
        return error_msg
    except Exception as e:
        logger.error(f"Error generating error message: {e}")
        # Fallback to basic message
        return "I encountered an error. Please try again."

async def get_clarification_message(field_name: str, lang_code: str = DEFAULT_LANGUAGE) -> str:
    """Generate a clarification request in the user's language."""
    system_prompt = f"""Generate a friendly clarification message in {lang_code} for a diet coaching app.
    Field: {field_name}
    
    The message should:
    1. Politely indicate we didn't understand their response
    2. Ask them to try again
    3. Be encouraging and supportive
    4. Use appropriate tone for the language/culture
    
    Keep the message friendly and helpful."""
    
    try:
        clarification = await chat_completion(
            system_prompt=system_prompt,
            user_message=f"Generate clarification request for: {field_name}"
        )
        return clarification
    except Exception as e:
        logger.error(f"Error generating clarification message: {e}")
        return f"Could you please clarify your {field_name}?"

async def process_incoming_message(phone_number: str, incoming_text: str) -> str:
    """Process incoming messages with comprehensive profile building."""
    try:
        # Ensure welcome message is initialized
        await ensure_welcome_message()
        
        # Log the incoming message with clear formatting
        logger.info("=" * 50)
        logger.info("INCOMING MESSAGE")
        logger.info(f"From: {phone_number[-4:]}")
        logger.info(f"Text: {incoming_text}")
        logger.info("=" * 50)

        # Get user profile and handle None case properly
        user_profile = await db.get_user_profile(phone_number)
        logger.info(f"Retrieved user profile: {json.dumps(user_profile, indent=2) if user_profile else 'None'}")
        
        # Get user's language or use default
        user_lang = user_profile.get("language", DEFAULT_LANGUAGE) if user_profile else DEFAULT_LANGUAGE
        
        # New user flow
        if not user_profile:
            logger.info(f"NEW USER DETECTED: {phone_number[-4:]}")
            
            # Create user profile
            if not await db.create_user_profile(phone_number):
                logger.error("Failed to create user profile")
                return await get_error_message("profile_creation_failed", user_lang)
            
            # Log messages
            if not await db.log_message(phone_number, "user", incoming_text):
                logger.error("Failed to log user message")
            
            if not await db.log_message(phone_number, "assistant", WELCOME_MESSAGE):
                logger.error("Failed to log welcome message")
            
            logger.info("=" * 50)
            logger.info("SENDING WELCOME MESSAGE:")
            logger.info(WELCOME_MESSAGE)
            logger.info("=" * 50)
            
            return WELCOME_MESSAGE

        # Language detection flow - check both missing language and undefined language
        if "language" not in user_profile or user_profile.get("language") == "und":
            try:
                logger.info("Processing language detection")
                detected_lang = await detect_language(incoming_text)
                detected_lang = detected_lang or "en"
                logger.info(f"Detected language: {detected_lang}")
                
                # Store only the language and step (known database columns)
                updates = {
                    "language": detected_lang,
                    "step": "language_detected"
                }
                logger.info(f"Updating user profile with: {json.dumps(updates, indent=2)}")
                
                if not await db.update_user_profile(phone_number, updates):
                    logger.error(f"Failed to store language for user: {phone_number[-4:]}")
                    return await get_error_message("language_detection_failed", user_lang)
                
                # Generate and send the introduction (which now includes asking for their name)
                coach_intro = await get_coach_intro(detected_lang)
                logger.info("=" * 50)
                logger.info("SENDING COACH INTRO:")
                logger.info(coach_intro)
                logger.info("=" * 50)
                
                if not await db.log_message(phone_number, "assistant", coach_intro):
                    logger.error("Failed to log coach intro")
                
                return coach_intro
                
            except Exception as e:
                logger.error(f"Error in language detection flow: {e}")
                return await get_error_message("language_detection_failed", user_lang)

        # Get next question before processing input
        current_field, next_question = await get_next_question(user_profile, user_profile.get("language", "en"))
        logger.info(f"Current field to fill: {current_field}")
        
        # If all required fields are complete, create the plan
        if current_field == "complete" and user_profile.get("step") != "chat":
            try:
                # Double check all required fields are filled
                missing_fields = [
                    field for field, info in PROFILE_FIELDS.items()
                    if info["required"] and (field not in user_profile or user_profile[field] is None)
                ]
                
                if missing_fields:
                    logger.info(f"Required fields still missing: {missing_fields}")
                    # Get question for first missing field
                    _, question = await get_next_question(
                        {"language": user_profile["language"]}, 
                        user_profile["language"]
                    )
                    return question
                
                # Generate and store the plan
                plan = await create_diet_plan(user_profile)
                if not await db.update_user_profile(phone_number, {
                    "step": "chat",
                    "plan": plan,
                    "plan_created_at": datetime.utcnow().isoformat()
                }):
                    logger.error(f"Failed to update user profile with plan: {phone_number[-4:]}")
                    return await get_error_message("plan_creation_failed", user_lang)
                
                # Send the plan
                response = f"Great! I've created a personalized plan for you based on your profile. {plan}"
                logger.info("=" * 50)
                logger.info("SENDING PLAN:")
                logger.info(response)
                logger.info("=" * 50)
                
                if not await db.log_message(phone_number, "assistant", response):
                    logger.error("Failed to log plan message")
                
                return response
                
            except Exception as e:
                logger.error(f"Error creating plan: {e}")
                return await get_error_message("plan_creation_failed", user_lang)
        
        # Process user input for the current field
        try:
            field_value = await extract_field_value(
                current_field, 
                incoming_text,
                user_profile.get("language", "en"),
                user_profile
            )
            
            logger.info(f"Extracted field value: {json.dumps(field_value, indent=2) if field_value else 'None'}")
            
            if field_value:
                # Update the user profile with the new field value
                if not await db.update_user_profile(phone_number, field_value):
                    logger.error(f"Failed to store field value for user: {phone_number[-4:]}")
                    return await get_error_message("field_value_storage_failed", user_lang)
                
                # Refresh user profile after update
                user_profile = await db.get_user_profile(phone_number)
                if not user_profile:
                    logger.error("Failed to retrieve updated user profile")
                    return await get_error_message("user_profile_retrieval_failed", user_lang)
                
                # Get the next question after successful update
                _, next_question = await get_next_question(user_profile, user_profile.get("language", "en"))
                logger.info("=" * 50)
                logger.info("SENDING NEXT QUESTION:")
                logger.info(next_question)
                logger.info("=" * 50)
                
                if not await db.log_message(phone_number, "assistant", next_question):
                    logger.error("Failed to log question message")
                
                return next_question
            
            # If we couldn't extract a value, send a more specific error message
            clarification = await get_clarification_message(current_field, user_profile.get("language", DEFAULT_LANGUAGE))
            response = f"{clarification} {next_question}"
            logger.info("=" * 50)
            logger.info("SENDING CLARIFICATION:")
            logger.info(response)
            logger.info("=" * 50)
            
            if not await db.log_message(phone_number, "assistant", response):
                logger.error("Failed to log clarification message")
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing field {current_field}: {e}")
            return await get_error_message("field_processing_failed", user_lang)
            
    except Exception as e:
        error_msg = f"Error Processing Message | Phone: {phone_number[-4:]} | Error: {str(e)}"
        logger.error("=" * 50)
        logger.error("ERROR OCCURRED:")
        logger.error(error_msg)
        logger.error("=" * 50)
        return await get_error_message("general_error", user_lang)

async def create_diet_plan(user_profile: Dict[str, Any]) -> str:
    """Create a personalized diet plan based on user profile."""
    system_prompt = """You are an expert diet and nutrition coach. Create a personalized plan based on this profile:
    Profile:
    {profile}
    
    Include:
    1. Daily calorie target
    2. Macronutrient distribution
    3. Meal timing recommendations
    4. Exercise suggestions
    5. Weekly weight loss/gain target
    6. Key recommendations
    
    Keep it concise but comprehensive.""".format(profile=json.dumps(user_profile, indent=2))
    
    try:
        plan = await chat_completion(
            system_prompt=system_prompt,
            user_message="Create plan"
        )
        return plan
    except Exception as e:
        logger.error(f"Error creating diet plan: {e}")
        return "Error creating plan. Please try again later."
