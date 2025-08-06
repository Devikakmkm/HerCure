import os
import requests
from flask import current_app
import json
import re
from datetime import datetime

class WellnessRecommendationError(Exception):
    """Custom exception for wellness recommendation errors"""
    pass

def test_point_parsing():
    """Test function to verify point parsing logic"""
    import sys
    import io
    
    # Set stdout to handle Unicode
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    test_content = """
    Nutrition
    ### Nutrition Plan 1. Stay hydrated by drinking at least 8 glasses of water daily. 2. Include a variety of colorful fruits and vegetables in your meals. 3. Choose whole grains over refined carbohydrates. 4. Consider iron-rich foods if you experience heavy periods.
    Exercise
    ### Exercise Plan 1. Aim for at least 30 minutes of moderate exercise most days. 2. Include both cardio and strength training in your routine. 3. Listen to your body and adjust intensity based on your energy levels. 4. Consider yoga or stretching for flexibility and stress relief.
    Sleep
    ### Sleep Plan 1. Maintain a consistent sleep schedule, even on weekends. 2. Create a relaxing bedtime routine. 3. Keep your bedroom cool, dark, and quiet. 4. Avoid screens for at least an hour before bedtime.
    """
    
    def print_section(title, content):
        print(f"\n{'='*40}")
        print(f"{title.upper()} SECTION")
        print('-'*40)
        result = format_section(title, content)
        # Print the result with proper encoding
        try:
            print(result)
        except UnicodeEncodeError:
            print(result.encode('utf-8').decode('ascii', 'ignore'))
    
    # Test Nutrition section
    nutrition_content = re.search(r'Nutrition.*?(?=Exercise|$)', test_content, re.DOTALL).group(0)
    print_section('Nutrition', nutrition_content)
    
    # Test Exercise section
    exercise_content = re.search(r'Exercise.*?(?=Sleep|$)', test_content, re.DOTALL).group(0)
    print_section('Exercise', exercise_content)
    
    # Test Sleep section
    sleep_content = re.search(r'Sleep.*?(?=$)', test_content, re.DOTALL).group(0)
    print_section('Sleep', sleep_content)

def format_section(title, content):
    """Format a section of the wellness recommendations with proper formatting and word limit.
    
    Args:
        title (str): Section title (Nutrition, Exercise, Sleep)
        content (str): Raw content of the section
        
    Returns:
        str: Formatted section content with proper markdown formatting
    """
    if not content or not content.strip():
        return f"### 🍽️ {title} Plan\nNo specific recommendations available.\n"
    
    content = content.strip()
    
    # Remove any duplicate section headers
    content = re.sub(r'(?i)^\s*#*\s*' + re.escape(title) + '\s*Plan\s*#*\s*', '', content)
    
    # First, clean up the content
    content = content.strip()
    
    # Remove any markdown headers and the title if present
    content = re.sub(r'#+\s*', '', content)
    content = re.sub(f'^{re.escape(title)}[^\n]*', '', content, flags=re.IGNORECASE).strip()
    
    # Try to find all numbered points using a more comprehensive approach
    points = []
    
    # First, try to find points in format "1. Point 2. Point"
    point_pattern = r'(?:^|\s)(\d+\.\s*[^\d]+?)(?=\s*\d+\.|\s*$)'
    point_matches = re.finditer(point_pattern, content)
    
    # If we found matches, extract them
    found_points = [match.group(1).strip() for match in point_matches]
    
    if found_points:
        points = found_points
    else:
        # If no matches, try splitting by numbers followed by a dot and space
        points = re.split(r'(?<=\d)\.\s+', content)
        
        # If we only got one point, try a different approach
        if len(points) <= 1:
            # Try to find points that start with a number and a dot
            point_pattern = r'(\d+\.\s*[^\d]+?)(?=\s*\d+\.|\s*$)'
            point_matches = re.findall(point_pattern, content)
            if point_matches:
                points = point_matches
            else:
                # As a last resort, split by periods that look like sentence endings
                points = re.split(r'(?<=\w)\.\s+(?=[A-Z])', content)
                
                # If still no luck, just split by periods
                if len(points) <= 1:
                    points = [p.strip() + '.' for p in content.split('.') if p.strip()]
    
    # Clean up the points
    points = [p.strip() for p in points if p.strip()]
    
    # If we have points but they don't start with numbers, add bullet points
    if points and not re.match(r'^\d+\.', points[0]):
        points = [f"• {p}" for p in points]
    
    # Process each point to ensure proper formatting
    formatted_points = []
    word_count = 0
    
    for point in points:
        # Clean up the point
        point = re.sub(r'\s+', ' ', point).strip()
        if not point:
            continue
            
        # Check word count
        words = point.split()
        if word_count + len(words) > 100:
            break
            
        # Add to formatted points with proper spacing
        if point[0].isdigit() and '. ' in point:
            # It's a numbered point
            formatted_points.append(point)
        else:
            # It's a regular point
            formatted_points.append(f"• {point}")
            
        word_count += len(words)
    
    # Join points with double newlines for spacing
    formatted_text = '\n\n'.join(formatted_points)
    
    # Add emoji based on section
    emoji = {
        'Nutrition': '🍽️',
        'Exercise': '🏃‍♀️',
        'Sleep': '😴',
        'Additional': '💡',
        'Profile': '👤',
        'Plan': '🌿'
    }.get(title, '✨')
    
    # Format the final output with proper spacing
    if title in ['Profile', 'Plan']:
        return f"### {emoji} {title} ###\n\n{formatted_text}\n"
    return f"### {emoji} {title} Plan ###\n\n{formatted_text}\n"

def generate_wellness_recommendations(user_profile):
    """
    Generates personalized wellness recommendations using the Groq API and LLaMA 3 model.
    
    Args:
        user_profile (dict): Dictionary containing user's health profile including:
            - age (int): User's age
            - cycle_info (dict): Information about menstrual cycle
            - recent_symptoms (list): List of recent symptoms
            
    Returns:
        dict: Dictionary containing wellness recommendations for nutrition, exercise, and sleep
    """
    # Configuration
    API_KEY = current_app.config.get('GROQ_API_KEY')
    if not API_KEY:
        current_app.logger.error("GROQ_API_KEY not found in app config")
        raise WellnessRecommendationError("API key not configured in application settings. Please contact support.")
    
    API_URL = "https://api.groq.com/openai/v1/chat/completions"
    
    # Default recommendations in case of any error
    default_recommendations = {
        'nutrition': '### Nutrition Plan\n1. Stay hydrated by drinking at least 8 glasses of water daily.\n2. Include a variety of colorful fruits and vegetables in your meals.\n3. Choose whole grains over refined carbohydrates.\n4. Consider iron-rich foods if you experience heavy periods.',
        'exercise': '### Exercise Plan\n1. Aim for at least 30 minutes of moderate exercise most days.\n2. Include both cardio and strength training in your routine.\n3. Listen to your body and adjust intensity based on your energy levels.\n4. Consider yoga or stretching for flexibility and stress relief.',
        'sleep': '### Sleep Plan\n1. Maintain a consistent sleep schedule, even on weekends.\n2. Create a relaxing bedtime routine.\n3. Keep your bedroom cool, dark, and quiet.\n4. Avoid screens for at least an hour before bedtime.'
    }
    
    try:
        # Extract cycle information with defaults
        cycle_length = user_profile.get('cycle_info', {}).get('average_cycle_length', 'irregular')
        period_length = user_profile.get('cycle_info', {}).get('average_period_length', 'irregular')
        symptoms = ", ".join(user_profile.get('recent_symptoms', [])) or "No specific symptoms reported"
        age = user_profile.get('age', 'Not specified')
        
        # Create a detailed prompt
        prompt = (
            f"Generate a personalized wellness plan for a woman with the following profile:\n"
            f"- Age: {age}\n"
            f"### 🌿 Your Personalized Wellness Plan 🌿\n\n"
            f"👤 **Profile Summary**\n"
            f"- 🔄 Average cycle: {cycle_length} days | 📅 Period: {period_length} days\n"
            f"- 🤒 Recent symptoms: {symptoms}\n\n"
            "### 🍽️ Nutrition Plan\n"
            "Focus on foods that support your cycle and overall well-being. Here are some recommendations:\n"
            "1. **Hydration**: Start your day with warm lemon water to aid digestion and hydration.\n"
            "2. **Balanced Meals**: Include a mix of complex carbs, lean proteins, and healthy fats in each meal.\n"
            "3. **Key Nutrients**: Ensure adequate intake of iron, magnesium, and omega-3s to support your cycle.\n\n"
            "### 🏃‍♀️ Exercise Plan\n"
            "Tailored movement for your cycle phase and symptoms. Consider these activities:\n"
            "1. **Gentle Movement**: Yoga or walking during your period for comfort.\n"
            "2. **Strength Training**: 2-3 times a week to support bone health.\n"
            "3. **Rest Days**: Listen to your body and take rest when needed.\n\n"
            "### 😴 Sleep Plan\n"
            "Quality sleep is crucial for hormonal balance. Try these tips:\n"
            "1. **Consistent Schedule**: Go to bed and wake up at the same time daily.\n"
            "2. **Wind Down**: Create a relaxing bedtime routine without screens.\n"
            "3. **Comfortable Environment**: Keep your bedroom cool, dark, and quiet.\n\n"
            "### 💡 Additional Tips\n"
            "- Track your symptoms to identify patterns.\n"
            "- Practice stress-reduction techniques like meditation.\n"
            "- Stay hydrated and limit caffeine and processed foods.\n\n"
            "*Remember, these are general recommendations. Always consult with a healthcare provider for personalized advice.*"
        )
        
        # API request headers
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Prepare the API payload
        payload = {
            "model": "llama3-8b-8192",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a compassionate and knowledgeable women's health specialist. "
                        "Provide practical, evidence-based wellness recommendations. "
                        "Be empathetic, professional, and focus on actionable advice. "
                        "Format your response with clear headings for Nutrition Plan, Exercise Plan, "
                        "and Sleep Plan, each with 3-4 specific recommendations."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 1000,
            "top_p": 0.9
        }
        
        # Log the API request for debugging
        current_app.logger.info(f"Sending request to Groq API with payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()

        result = response.json()
        current_app.logger.info(f"Received response from Groq API: {json.dumps(result, indent=2)}")
        
        if 'choices' not in result or not result['choices']:
            raise ValueError("Invalid response format from Groq API: missing 'choices' field")
            
        content = result['choices'][0].get('message', {}).get('content', '')
        
        if not content:
            raise ValueError("Empty content in Groq API response")

        # Try to parse the response for specific recommendations
        recommendations = default_recommendations.copy()
        try:
            # First, clean up the content
            content = ' '.join(line.strip() for line in content.split('\n') if line.strip())
            
            # Define section patterns to split on
            section_patterns = [
                (r'(?i)###?\s*Nutrition\s*Plan', 'nutrition'),
                (r'(?i)###?\s*Exercise\s*Plan', 'exercise'),
                (r'(?i)###?\s*Sleep\s*Plan', 'sleep')
            ]
            
            # Find all section starts
            section_starts = []
            for pattern, section_type in section_patterns:
                for match in re.finditer(pattern, content):
                    section_starts.append((match.start(), section_type))
            
            # Sort sections by their start position
            section_starts.sort()
            
            # Extract each section's content
            for i, (start_pos, section_type) in enumerate(section_starts):
                # Find the end of this section (start of next section or end of content)
                end_pos = section_starts[i+1][0] if i+1 < len(section_starts) else None
                section_content = content[start_pos:end_pos].strip()
                
                # Remove the section header
                section_content = re.sub(r'^###?\s*\w+\s*Plan\s*', '', section_content, flags=re.IGNORECASE)
                
                # Clean up any remaining section headers
                section_content = re.sub(r'(?i)###?\s*(?:Nutrition|Exercise|Sleep)\s*Plan\s*', '', section_content)
                
                # Format and store the section
                if section_content.strip():
                    recommendations[section_type] = format_section(section_type.title(), section_content)
                    
        except Exception as parse_error:
            current_app.logger.warning(f"Error parsing API response: {parse_error}", exc_info=True)
            # Use the raw content if parsing fails
            if content:
                recommendations = {
                    'nutrition': format_section('Nutrition', content),
                    'exercise': format_section('Exercise', content),
                    'sleep': format_section('Sleep', content)
                }

        return recommendations
        
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Error calling Groq API: {str(e)}")
        return default_recommendations
        
    except json.JSONDecodeError as e:
        current_app.logger.error(f"Error decoding JSON response: {str(e)}")
        return default_recommendations
        
    except Exception as e:
        current_app.logger.error(f"Unexpected error in generate_wellness_recommendations: {str(e)}", exc_info=True)
        return default_recommendations
