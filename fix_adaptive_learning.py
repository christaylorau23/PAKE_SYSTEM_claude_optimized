#!/usr/bin/env python3
"""Targeted script to fix remaining F821 errors in adaptive_learning_engine.py"""

import re

def fix_adaptive_learning_engine():
    """Fix F821 errors in adaptive_learning_engine.py"""
    
    file_path = "/home/chris/PAKE_SYSTEM_claude_optimized/src/services/ai/adaptive_learning_engine.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix method signatures based on the F821 errors found
    fixes = [
        # update_user_interactions method
        (
            r'def update_user_interactions\(self\) -> None:\n        """Update the collaborative filtering model with new interactions."""\n        for interaction in interactions:',
            'def update_user_interactions(self, interactions: List[UserInteraction]) -> None:\n        """Update the collaborative filtering model with new interactions."""\n        for interaction in interactions:'
        ),
        
        # update_content_features method
        (
            r'def update_content_features\(self\) -> None:\n        """Update content features for content-based filtering."""\n        self\.content_features\[content_id\] = features',
            'def update_content_features(self, content_id: str, features: Dict[str, float]) -> None:\n        """Update content features for content-based filtering."""\n        self.content_features[content_id] = features'
        ),
        
        # get_user_recommendations method
        (
            r'def get_user_recommendations\(self\) -> List\[str\]:\n        """Get personalized recommendations for a user."""\n        if user_id not in self\.user_profiles:',
            'def get_user_recommendations(self, user_id: str) -> List[str]:\n        """Get personalized recommendations for a user."""\n        if user_id not in self.user_profiles:'
        ),
        
        # update_user_profile method
        (
            r'def update_user_profile\(self\) -> None:\n        """Update user profile based on recent interactions."""\n        if user_id not in self\.user_profiles:',
            'def update_user_profile(self, user_id: str) -> None:\n        """Update user profile based on recent interactions."""\n        if user_id not in self.user_profiles:'
        ),
        
        # record_user_interaction method
        (
            r'def record_user_interaction\(self\) -> None:\n        """Record a user interaction for learning."""\n        if user_id not in self\.user_interactions:',
            'def record_user_interaction(self, user_id: str, interaction: UserInteraction) -> None:\n        """Record a user interaction for learning."""\n        if user_id not in self.user_interactions:'
        ),
    ]
    
    # Apply fixes
    for pattern, replacement in fixes:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    
    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Fixed adaptive_learning_engine.py")

if __name__ == "__main__":
    fix_adaptive_learning_engine()
