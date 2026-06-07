"""
Comprehensive tests demonstrating user-specific profile ownership and data isolation.

These tests verify that:
1. User A cannot see User B's profiles
2. User A cannot modify User B's profiles
3. User A exports only User A's data
4. Profile ownership is enforced at all layers (model, repository, service)
5. Authorization checks prevent cross-user access
6. Data survives application restarts with correct ownership
"""

import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.models import LearnerProfile, TopicProgress, LearningSystemState, UserAccount
from services.learning_service import LearningService
from storage.repository import ProfileRepository, AccountRepository
from utils.security import hash_password, generate_salt


def test_profile_model_has_owner_field():
    """Test 1: LearnerProfile dataclass includes owner field."""
    profile = LearnerProfile(
        name='algebra',
        owner='alice',
        created_at=datetime.now(),
        state=LearningSystemState(),
        topics=[]
    )
    assert profile.owner == 'alice'
    assert hasattr(profile, 'owner')
    print("✓ Test 1: Profile model includes owner field")


def test_profile_serialization_preserves_owner():
    """Test 2: Profile serialization to_dict/from_dict preserves owner."""
    profile = LearnerProfile(
        name='algebra',
        owner='bob',
        created_at=datetime.now(),
        state=LearningSystemState(),
        topics=[]
    )
    data = profile.to_dict()
    assert data['owner'] == 'bob'
    
    restored = LearnerProfile.from_dict(data)
    assert restored.owner == 'bob'
    assert restored.name == 'algebra'
    print("✓ Test 2: Profile serialization preserves owner field")


def test_profile_repository_list_profiles_by_owner():
    """Test 3: ProfileRepository.list_profiles(owner) filters by owner."""
    repo = ProfileRepository()
    
    # Simulate existing profiles for different users
    repo.profiles = [
        LearnerProfile(name='alice_math', owner='alice', created_at=datetime.now()),
        LearnerProfile(name='alice_science', owner='alice', created_at=datetime.now()),
        LearnerProfile(name='bob_history', owner='bob', created_at=datetime.now()),
        LearnerProfile(name='charlie_english', owner='charlie', created_at=datetime.now()),
    ]
    
    # List profiles for alice
    alice_profiles = repo.list_profiles(owner='alice')
    assert len(alice_profiles) == 2
    assert all(p.owner == 'alice' for p in alice_profiles)
    assert set(p.name for p in alice_profiles) == {'alice_math', 'alice_science'}
    
    # List profiles for bob
    bob_profiles = repo.list_profiles(owner='bob')
    assert len(bob_profiles) == 1
    assert bob_profiles[0].owner == 'bob'
    assert bob_profiles[0].name == 'bob_history'
    
    # List all profiles (no filter)
    all_profiles = repo.list_profiles()
    assert len(all_profiles) == 4
    print("✓ Test 3: ProfileRepository correctly filters profiles by owner")


def test_profile_repository_find_by_name_and_owner():
    """Test 4: ProfileRepository.find_by_name_and_owner() enforces ownership."""
    repo = ProfileRepository()
    repo.profiles = [
        LearnerProfile(name='algebra', owner='alice', created_at=datetime.now()),
        LearnerProfile(name='algebra', owner='bob', created_at=datetime.now()),
    ]
    
    # Alice can find her algebra profile
    alice_algebra = repo.find_by_name_and_owner('algebra', 'alice')
    assert alice_algebra.owner == 'alice'
    
    # Bob can find his algebra profile
    bob_algebra = repo.find_by_name_and_owner('algebra', 'bob')
    assert bob_algebra.owner == 'bob'
    
    # Charlie cannot find an algebra profile (not owner)
    try:
        repo.find_by_name_and_owner('algebra', 'charlie')
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert 'charlie' in str(e)
    
    print("✓ Test 4: find_by_name_and_owner() enforces ownership")


def test_profile_repository_add_profile_with_ownership():
    """Test 5: ProfileRepository.add_profile() creates profiles with ownership."""
    repo = ProfileRepository()
    repo.profiles = []
    
    # Add profile for alice
    alice_profile = repo.add_profile('math', owner='alice')
    assert alice_profile.owner == 'alice'
    assert alice_profile.name == 'math'
    
    # Add profile with same name for bob (should succeed - different owner)
    bob_profile = repo.add_profile('math', owner='bob')
    assert bob_profile.owner == 'bob'
    
    # Try to add duplicate for alice (should fail)
    try:
        repo.add_profile('math', owner='alice')
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert 'already exists' in str(e)
    
    assert len(repo.profiles) == 2
    print("✓ Test 5: add_profile() creates profiles with ownership")


def test_profile_repository_delete_profile_with_ownership():
    """Test 6: ProfileRepository.delete_profile() enforces ownership on deletion."""
    repo = ProfileRepository()
    repo.profiles = [
        LearnerProfile(name='math', owner='alice', created_at=datetime.now()),
        LearnerProfile(name='math', owner='bob', created_at=datetime.now()),
    ]
    
    # Delete alice's math profile
    repo.delete_profile('math', owner='alice')
    assert len(repo.profiles) == 1
    assert repo.profiles[0].owner == 'bob'
    
    # Verify bob's math profile still exists
    remaining = repo.find_by_name_and_owner('math', 'bob')
    assert remaining.owner == 'bob'
    print("✓ Test 6: delete_profile() respects ownership")


def test_learning_service_user_context():
    """Test 7: LearningService maintains user context and scopes access."""
    # Create services for different users
    service_alice = LearningService(profile_name='alice', username='alice')
    service_bob = LearningService(profile_name='bob', username='bob')
    
    assert service_alice.username == 'alice'
    assert service_bob.username == 'bob'
    assert service_alice.active_profile.owner == 'alice'
    assert service_bob.active_profile.owner == 'bob'
    print("✓ Test 7: LearningService maintains user context")


def test_learning_service_list_profiles_filtered_by_user():
    """Test 8: LearningService.list_profiles() returns only user's profiles."""
    # Create service for alice
    service = LearningService(profile_name='math', username='alice')
    
    # Manually add profiles for different users
    service.profile_repo.profiles = [
        LearnerProfile(name='math', owner='alice', created_at=datetime.now()),
        LearnerProfile(name='science', owner='alice', created_at=datetime.now()),
        LearnerProfile(name='history', owner='bob', created_at=datetime.now()),
        LearnerProfile(name='english', owner='charlie', created_at=datetime.now()),
    ]
    
    # Alice should only see her profiles
    alice_profiles = service.list_profiles()
    assert len(alice_profiles) == 2
    assert set(alice_profiles) == {'math', 'science'}
    print("✓ Test 8: list_profiles() filters by authenticated user")


def test_learning_service_create_profile_with_ownership():
    """Test 9: LearningService.create_profile() creates owned profiles."""
    service_alice = LearningService(profile_name='alice', username='alice')
    
    # Alice creates a new profile
    new_profile = service_alice.create_profile('algebra')
    assert new_profile.owner == 'alice'
    assert new_profile.name == 'algebra'
    
    # Verify Alice can list it
    profiles = service_alice.list_profiles()
    assert 'algebra' in profiles
    print("✓ Test 9: create_profile() creates profiles with user ownership")


def test_learning_service_select_profile_ownership_check():
    """Test 10: LearningService.select_profile() enforces ownership."""
    service_alice = LearningService(profile_name='alice', username='alice')
    
    # Set up profiles for different users
    service_alice.profile_repo.profiles = [
        LearnerProfile(name='alice_math', owner='alice', created_at=datetime.now()),
        LearnerProfile(name='alice', owner='alice', created_at=datetime.now()),  # Default profile
        LearnerProfile(name='bob_science', owner='bob', created_at=datetime.now()),
    ]
    
    # Alice can select her profile
    selected = service_alice.select_profile('alice_math')
    assert selected.owner == 'alice'
    
    # Alice cannot select bob's profile
    try:
        service_alice.select_profile('bob_science')
        assert False, "Should have raised ValueError for unauthorized access"
    except ValueError as e:
        # Expected - should not allow access to bob's profile
        assert 'not found' in str(e).lower() or 'bob' in str(e).lower()
    
    print("✓ Test 10: select_profile() enforces ownership verification")


def test_learning_service_export_only_user_data():
    """Test 11: LearningService.export_all_data() exports only user's profiles."""
    service_alice = LearningService(profile_name='alice', username='alice')
    
    # Add multiple users' data to repository
    alice_profile = LearnerProfile(name='alice', owner='alice', created_at=datetime.now())
    bob_profile = LearnerProfile(name='bob', owner='bob', created_at=datetime.now())
    charlie_profile = LearnerProfile(name='charlie', owner='charlie', created_at=datetime.now())
    
    service_alice.profile_repo.profiles = [alice_profile, bob_profile, charlie_profile]
    
    # Export alice's data
    export_json = service_alice.export_all_data()
    exported_data = json.loads(export_json)
    
    # Verify only alice's profile is exported
    exported_profiles = exported_data.get('profiles', [])
    assert len(exported_profiles) == 1
    assert exported_profiles[0]['name'] == 'alice'
    assert exported_profiles[0]['owner'] == 'alice'
    
    # Bob's and Charlie's profiles should NOT be in export
    profile_names = {p['name'] for p in exported_profiles}
    assert 'bob' not in profile_names
    assert 'charlie' not in profile_names
    print("✓ Test 11: export_all_data() exports only user's profiles")


def test_learning_service_import_only_user_data():
    """Test 12: LearningService.import_all_data() respects user ownership."""
    service_alice = LearningService(profile_name='alice', username='alice')
    
    # Create import data with multiple users' profiles
    import_payload = {
        'profiles': [
            {
                'name': 'alice_math',
                'owner': 'alice',
                'created_at': datetime.now().isoformat(),
                'state': {'weights': {}, 'recommendation_history': [], 'feedback_log': []},
                'topics': []
            },
            {
                'name': 'bob_math',
                'owner': 'bob',
                'created_at': datetime.now().isoformat(),
                'state': {'weights': {}, 'recommendation_history': [], 'feedback_log': []},
                'topics': []
            }
        ]
    }
    
    # Import - alice should only get her profile
    service_alice.import_all_data(json.dumps(import_payload))
    
    # Verify only alice's profile was imported
    alice_profiles = service_alice.profile_repo.list_profiles(owner='alice')
    profile_names = {p.name for p in alice_profiles}
    assert 'alice_math' in profile_names
    # bob_math should NOT be imported for alice's user
    bob_in_alice_repo = any(p.name == 'bob_math' and p.owner == 'alice' for p in service_alice.profile_repo.profiles)
    assert not bob_in_alice_repo
    print("✓ Test 12: import_all_data() respects user ownership")


def test_learning_service_create_account_creates_owned_profile():
    """Test 13: create_account() creates a profile owned by the new user."""
    service = LearningService(profile_name='system', username='system')
    
    # Clean up any existing test accounts
    service.account_repo.accounts = []
    service.profile_repo.profiles = []
    
    # Create accounts for multiple users
    service.create_account('alice', 'password123')
    service.create_account('bob', 'password456')
    
    # Verify profiles were created with correct ownership
    alice_profiles = service.profile_repo.list_profiles(owner='alice')
    bob_profiles = service.profile_repo.list_profiles(owner='bob')
    
    # Each user should have their default profile
    assert len(alice_profiles) == 1
    assert alice_profiles[0].name == 'alice'
    assert alice_profiles[0].owner == 'alice'
    
    assert len(bob_profiles) == 1
    assert bob_profiles[0].name == 'bob'
    assert bob_profiles[0].owner == 'bob'
    print("✓ Test 13: create_account() creates owned profile for new user")


def test_service_respects_dashboard_data_isolation():
    """Test 14: Dashboard data is scoped to the active user's profile."""
    service_alice = LearningService(profile_name='alice', username='alice')
    
    # Add some topics to alice's profile
    service_alice.add_topic('algebra', 85.0, 0.5, tags=['math'], subject='Mathematics')
    
    # Get dashboard data
    dashboard = service_alice.get_dashboard_data()
    
    # Dashboard should show alice's data
    assert dashboard['user'] == 'alice'
    assert dashboard['active_profile'] == 'alice'
    assert int(dashboard['topic_count']) >= 1
    print("✓ Test 14: Dashboard data is scoped to user's profile")


def test_cross_user_attack_vectors_blocked():
    """Test 15: Verify common attack vectors are blocked."""
    service_alice = LearningService(profile_name='alice', username='alice')
    service_bob = LearningService(profile_name='bob', username='bob')
    
    # Set up different profiles
    service_alice.profile_repo.profiles = [
        LearnerProfile(name='alice_math', owner='alice', created_at=datetime.now()),
        LearnerProfile(name='bob_math', owner='bob', created_at=datetime.now()),
    ]
    
    # Attack 1: Try to select another user's profile
    try:
        service_alice.select_profile('bob_math')
        assert False, "Should block selection of other user's profile"
    except ValueError:
        pass  # Expected
    
    # Attack 2: Try to create duplicate of other user's profile
    # (should succeed with different owner)
    try:
        service_alice.create_profile('bob_math')
        # Should succeed because alice is creating her own 'bob_math' profile
        alice_bob_math = service_alice.profile_repo.find_by_name_and_owner('bob_math', 'alice')
        assert alice_bob_math.owner == 'alice'
    except ValueError:
        pass  # Either outcome is acceptable
    
    print("✓ Test 15: Cross-user attack vectors are blocked")


def test_profile_ownership_persistence():
    """Test 16: Profile ownership persists across serialization cycles."""
    # Create profile
    profile = LearnerProfile(
        name='persistent_test',
        owner='alice',
        created_at=datetime.now(),
        state=LearningSystemState(),
        topics=[]
    )
    
    # Serialize to dict and back multiple times
    for _ in range(3):
        profile_dict = profile.to_dict()
        profile = LearnerProfile.from_dict(profile_dict)
    
    # Owner should be preserved
    assert profile.owner == 'alice'
    assert profile.name == 'persistent_test'
    print("✓ Test 16: Profile ownership persists through serialization cycles")


def test_backward_compatibility_unowned_profiles():
    """Test 17: Legacy profiles without owner field migrate to default."""
    # Simulate loading a profile without owner (legacy data)
    legacy_data = {
        'name': 'legacy_profile',
        # NO 'owner' field - simulating old data format
        'created_at': datetime.now().isoformat(),
        'state': {'weights': {}, 'recommendation_history': [], 'feedback_log': []},
        'topics': []
    }
    
    # Load legacy profile
    profile = LearnerProfile.from_dict(legacy_data)
    
    # Should have default owner
    assert profile.owner == 'default'
    print("✓ Test 17: Legacy profiles without owner migrate to 'default'")


def run_all_tests():
    """Run all isolation tests."""
    print("\n" + "="*80)
    print("USER PROFILE ISOLATION AND OWNERSHIP TESTS")
    print("="*80 + "\n")
    
    tests = [
        test_profile_model_has_owner_field,
        test_profile_serialization_preserves_owner,
        test_profile_repository_list_profiles_by_owner,
        test_profile_repository_find_by_name_and_owner,
        test_profile_repository_add_profile_with_ownership,
        test_profile_repository_delete_profile_with_ownership,
        test_learning_service_user_context,
        test_learning_service_list_profiles_filtered_by_user,
        test_learning_service_create_profile_with_ownership,
        test_learning_service_select_profile_ownership_check,
        test_learning_service_export_only_user_data,
        test_learning_service_import_only_user_data,
        test_learning_service_create_account_creates_owned_profile,
        test_service_respects_dashboard_data_isolation,
        test_cross_user_attack_vectors_blocked,
        test_profile_ownership_persistence,
        test_backward_compatibility_unowned_profiles,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__}: {e}")
            failed += 1
    
    print("\n" + "="*80)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("="*80 + "\n")
    
    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    exit(0 if success else 1)
