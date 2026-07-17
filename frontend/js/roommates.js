async function loadRoommateMatches() {
    const container = document.getElementById('roommatesContainer');
    if (!container) return;

    try {
        const data = await api.getRoommateMatches(); // Add getRoommateMatches to api.js pointing to GET /roommates/matches
        container.innerHTML = '';

        if (!data.matches || data.matches.length === 0) {
            container.innerHTML = '<p style="color: var(--text-muted);">No roommate matches found in your area right now.</p>';
            return;
        }

        data.matches.forEach(peer => {
            const card = document.createElement('div');
            card.className = 'roommate-card';
            card.style.cssText = 'background: white; padding: 1.25rem; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.04); display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;';
            
            card.innerHTML = `
                <div>
                    <h4 style="margin-bottom: 0.25rem;">${peer.name}</h4>
                    <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.25rem;">Preferred Area: <strong>${peer.area}</strong></p>
                    <span style="background: #eef2ff; color: #4f46e5; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600;">${peer.compatibility_score}</span>
                </div>
                <button class="btn btn-blue-outline" style="padding: 0.4rem 1rem; font-size: 0.85rem;" onclick="sendSplitInvite(${peer.id})">Invite to Split</button>
            `;
            container.appendChild(card);
        });
    } catch (e) {
        console.error("Error loading roommates", e);
    }
}