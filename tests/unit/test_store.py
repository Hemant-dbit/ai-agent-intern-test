from app.session.store import SessionStore

def test_session_isolation():
    store = SessionStore()
    store.record_turn("session-1", "user", "Hello 1")
    store.set_active_order("session-1", "ORD-1")
    store.set_active_topic("session-1", "Returns")

    store.record_turn("session-2", "user", "Hello 2")
    store.set_active_order("session-2", "ORD-2")
    
    session1 = store.get_or_create("session-1")
    session2 = store.get_or_create("session-2")
    
    assert session1.turns[0].content == "Hello 1"
    assert session1.active_order_id == "ORD-1"
    assert session1.active_topic == "Returns"
    
    assert session2.turns[0].content == "Hello 2"
    assert session2.active_order_id == "ORD-2"
    assert session2.active_topic is None

def test_recent_turns_respects_cap():
    store = SessionStore()
    for i in range(10):
        store.record_turn("session-1", "user", f"Message {i}")
    
    recent = store.get_recent_turns("session-1", n=6)
    assert len(recent) == 6
    assert recent[0].content == "Message 4"
    assert recent[-1].content == "Message 9"
    
    # Internal turns list still has all 10
    assert len(store.get_or_create("session-1").turns) == 10

def test_set_active_order_overwrites():
    store = SessionStore()
    store.set_active_order("session-1", "ORD-1")
    assert store.get_or_create("session-1").active_order_id == "ORD-1"
    
    store.set_active_order("session-1", "ORD-2")
    assert store.get_or_create("session-1").active_order_id == "ORD-2"
