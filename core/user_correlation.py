#!/usr/bin/env python3
"""
User Correlation Algorithm  
Intelligent matching of users across different database systems
"""

import re
from typing import Dict, List, Optional, Tuple
from difflib import SequenceMatcher
import logging
from datetime import datetime

class UserCorrelationEngine:
    """Intelligent user correlation and matching system"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Scoring weights for different matching criteria
        self.weights = {
            'exact_match': 1.0,
            'username_similarity': 0.8,
            'email_match': 0.9,
            'display_name_similarity': 0.7,
            'pattern_match': 0.6,
            'role_similarity': 0.5,
            'creation_time_proximity': 0.3
        }
        
        # Common username patterns
        self.common_patterns = [
            r'^([a-zA-Z]+)\.([a-zA-Z]+)$',  # first.last
            r'^([a-zA-Z])([a-zA-Z]+)$',     # flast  
            r'^([a-zA-Z]+)_([a-zA-Z]+)$',   # first_last
            r'^([a-zA-Z]+)([0-9]+)$',       # username123
            r'^([a-zA-Z]{2,3})([0-9]+)$',   # ab123
        ]
    
    def find_potential_matches(self, new_user: Dict, existing_users: List[Dict], 
                              min_confidence: float = 0.3) -> List[Tuple[Dict, float]]:
        """Find potential matches for a new user among existing users"""
        matches = []
        
        for existing_user in existing_users:
            confidence = self.calculate_match_confidence(new_user, existing_user)
            
            if confidence >= min_confidence:
                matches.append((existing_user, confidence))
        
        # Sort by confidence score, descending
        matches.sort(key=lambda x: x[1], reverse=True)
        
        self.logger.info(f"Found {len(matches)} potential matches for user {new_user.get('username', 'Unknown')}")
        
        return matches
    
    def calculate_match_confidence(self, user1: Dict, user2: Dict) -> float:
        """Calculate confidence score for two users being the same person"""
        scores = []
        
        # Extract normalized usernames
        username1 = self._normalize_username(user1.get('username', ''))
        username2 = self._normalize_username(user2.get('username', ''))
        
        if not username1 or not username2:
            return 0.0
        
        # 1. Exact username match (case-insensitive)
        if username1 == username2:
            scores.append(('exact_match', 1.0))
        else:
            # 2. Username similarity
            similarity = self._calculate_string_similarity(username1, username2)
            if similarity > 0.3:
                scores.append(('username_similarity', similarity))
            
            # 3. Pattern-based matching
            pattern_score = self._calculate_pattern_similarity(username1, username2)
            if pattern_score > 0.0:
                scores.append(('pattern_match', pattern_score))
        
        # 4. Email matching
        email1 = user1.get('email', '')
        email2 = user2.get('email', '')
        if email1 and email2:
            if email1.lower() == email2.lower():
                scores.append(('email_match', 1.0))
            else:
                # Check if email username parts match
                email_user1 = email1.split('@')[0].lower() if '@' in email1 else ''
                email_user2 = email2.split('@')[0].lower() if '@' in email2 else ''
                if email_user1 and email_user2:
                    email_sim = self._calculate_string_similarity(email_user1, email_user2)
                    if email_sim > 0.5:
                        scores.append(('email_match', email_sim * 0.7))
        
        # 5. Display name similarity
        display1 = user1.get('display_name', '')
        display2 = user2.get('display_name', '')
        if display1 and display2:
            display_sim = self._calculate_string_similarity(display1.lower(), display2.lower())
            if display_sim > 0.4:
                scores.append(('display_name_similarity', display_sim))
        
        # 6. Role/privilege similarity
        roles1 = set(user1.get('roles', []) or [])
        roles2 = set(user2.get('roles', []) or [])
        if roles1 and roles2:
            role_intersection = len(roles1.intersection(roles2))
            role_union = len(roles1.union(roles2))
            if role_union > 0:
                role_similarity = role_intersection / role_union
                if role_similarity > 0.2:
                    scores.append(('role_similarity', role_similarity))
        
        # 7. Creation time proximity
        created1 = user1.get('created_at') or user1.get('scan_time')
        created2 = user2.get('created_at') or user2.get('scan_time')
        if created1 and created2:
            time_score = self._calculate_time_proximity(created1, created2)
            if time_score > 0.1:
                scores.append(('creation_time_proximity', time_score))
        
        # Calculate weighted average
        total_weighted_score = sum(score * self.weights.get(criterion, 0.5) 
                                 for criterion, score in scores)
        total_weight = sum(self.weights.get(criterion, 0.5) 
                         for criterion, _ in scores)
        
        if total_weight == 0:
            return 0.0
        
        confidence = min(total_weighted_score / total_weight, 1.0)
        
        self.logger.debug(f"Match confidence between {username1} and {username2}: {confidence:.3f} "
                         f"(criteria: {[c for c, _ in scores]})")
        
        return confidence
    
    def _normalize_username(self, username: str) -> str:
        """Normalize username for comparison"""
        if not username:
            return ""
        
        # Remove common prefixes/suffixes
        username = username.lower().strip()
        
        # Remove domain parts (user@domain -> user)
        if '@' in username:
            username = username.split('@')[0]
        
        # Remove common separators for comparison
        username_clean = re.sub(r'[._-]', '', username)
        
        return username_clean
    
    def _calculate_string_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings"""
        if not str1 or not str2:
            return 0.0
        
        # Use SequenceMatcher for similarity
        similarity = SequenceMatcher(None, str1.lower(), str2.lower()).ratio()
        
        # Boost score for substring matches
        if str1 in str2 or str2 in str1:
            similarity = max(similarity, 0.7)
        
        return similarity
    
    def _calculate_pattern_similarity(self, username1: str, username2: str) -> float:
        """Calculate similarity based on common username patterns"""
        best_score = 0.0
        
        for pattern in self.common_patterns:
            match1 = re.match(pattern, username1)
            match2 = re.match(pattern, username2)
            
            if match1 and match2:
                # Both usernames match the same pattern
                groups1 = match1.groups()
                groups2 = match2.groups()
                
                if len(groups1) == len(groups2):
                    # Compare groups
                    group_similarities = []
                    for g1, g2 in zip(groups1, groups2):
                        sim = self._calculate_string_similarity(g1, g2)
                        group_similarities.append(sim)
                    
                    # Average similarity of all groups
                    pattern_score = sum(group_similarities) / len(group_similarities)
                    best_score = max(best_score, pattern_score)
        
        return best_score
    
    def _calculate_time_proximity(self, time1: str, time2: str) -> float:
        """Calculate proximity score based on creation times"""
        try:
            # Parse ISO format timestamps
            dt1 = datetime.fromisoformat(time1.replace('Z', '+00:00'))
            dt2 = datetime.fromisoformat(time2.replace('Z', '+00:00'))
            
            # Calculate time difference in hours
            time_diff = abs((dt1 - dt2).total_seconds()) / 3600
            
            # Score based on proximity (closer = higher score)
            if time_diff < 1:  # Within 1 hour
                return 0.9
            elif time_diff < 24:  # Within 1 day
                return 0.7
            elif time_diff < 168:  # Within 1 week
                return 0.5
            elif time_diff < 720:  # Within 1 month
                return 0.3
            else:
                return 0.1
                
        except Exception as e:
            self.logger.debug(f"Error calculating time proximity: {e}")
            return 0.0
    
    def create_correlation_suggestion(self, new_user: Dict, potential_matches: List[Tuple[Dict, float]], 
                                    server_name: str) -> Dict:
        """Create a correlation suggestion with ranked matches"""
        
        suggestion = {
            'new_user': new_user,
            'server_name': server_name,
            'potential_matches': [],
            'confidence_scores': {},
            'recommendation': 'manual_review',
            'created_at': datetime.now().isoformat()
        }
        
        # Process matches
        for i, (match_user, confidence) in enumerate(potential_matches[:5]):  # Top 5 matches
            match_info = {
                'id': match_user.get('id'),
                'username': match_user.get('username'),
                'display_name': match_user.get('display_name'),
                'email': match_user.get('email'),
                'server_name': match_user.get('server_name'),
                'database_type': match_user.get('database_type'),
                'confidence': confidence
            }
            
            suggestion['potential_matches'].append(match_info)
            suggestion['confidence_scores'][str(i)] = confidence
        
        # Determine recommendation based on top match confidence
        if potential_matches:
            top_confidence = potential_matches[0][1]
            
            if top_confidence >= 0.9:
                suggestion['recommendation'] = 'auto_approve'
            elif top_confidence >= 0.7:
                suggestion['recommendation'] = 'suggest_approval'
            elif top_confidence >= 0.4:
                suggestion['recommendation'] = 'manual_review'
            else:
                suggestion['recommendation'] = 'create_new_user'
        else:
            suggestion['recommendation'] = 'create_new_user'
        
        return suggestion
    
    def batch_correlate_users(self, new_users: List[Dict], existing_users: List[Dict]) -> List[Dict]:
        """Perform batch correlation for multiple new users"""
        suggestions = []
        
        for new_user in new_users:
            # Find matches for this user
            matches = self.find_potential_matches(new_user, existing_users)
            
            if matches:
                suggestion = self.create_correlation_suggestion(
                    new_user, matches, new_user.get('server_name', 'Unknown')
                )
                suggestions.append(suggestion)
        
        self.logger.info(f"Generated {len(suggestions)} correlation suggestions for {len(new_users)} new users")
        
        return suggestions
    
    def get_correlation_statistics(self, suggestions: List[Dict]) -> Dict:
        """Get statistics about correlation suggestions"""
        stats = {
            'total_suggestions': len(suggestions),
            'auto_approve': 0,
            'suggest_approval': 0,
            'manual_review': 0,
            'create_new_user': 0,
            'average_confidence': 0.0,
            'high_confidence_matches': 0
        }
        
        total_confidence = 0.0
        
        for suggestion in suggestions:
            recommendation = suggestion.get('recommendation', 'manual_review')
            stats[recommendation] = stats.get(recommendation, 0) + 1
            
            # Calculate average confidence of top matches
            confidence_scores = suggestion.get('confidence_scores', {})
            if confidence_scores:
                top_confidence = confidence_scores.get('0', 0.0)
                total_confidence += top_confidence
                
                if top_confidence >= 0.8:
                    stats['high_confidence_matches'] += 1
        
        if suggestions:
            stats['average_confidence'] = total_confidence / len(suggestions)
        
        return stats

# Global correlation engine instance
_correlation_engine = None

def get_correlation_engine() -> UserCorrelationEngine:
    """Get the global correlation engine instance"""
    global _correlation_engine
    if _correlation_engine is None:
        _correlation_engine = UserCorrelationEngine()
    return _correlation_engine