// ==========================================================
// HOSTRA DASHBOARD UI (The Painter)
// Handles Navbar, Wallet, Notifications, and Split Invites.
// ==========================================================

document.addEventListener("DOMContentLoaded", () => {
    if (!session.isAuthenticated()) return;

    // 1. Load Live Navbar Data
    updateWalletUI();
    pollNotifications();
    setInterval(pollNotifications, 10000); // Check notifications every 10 seconds

    // 2. Load Split Invites (if container exists)
    if (document.getElementById("invitesContainer")) {
        loadSplitInvitesUI();
    }

    // 3. Setup Notification Bell Click Dropdown
    const bell = document.getElementById("notificationBell");
    const dropdown = document.getElementById("notificationDropdown");
    if (bell && dropdown) {
        bell.addEventListener("click", () => {
            dropdown.style.display = dropdown.style.display === "none" ? "block" : "none";
        });
    }
});

async function updateWalletUI() {
    const walletEl = document.getElementById("walletBalance");
    if (!walletEl) return;
    try {
        const data = await api.getWallet();
        if (data && data.wallet_balance !== undefined) {
            walletEl.innerText = `₦${data.wallet_balance.toLocaleString()}`;
        }
    } catch (err) {
        console.error("Failed to update wallet UI:", err);
    }
}

async function pollNotifications() {
    const listContainer = document.getElementById("notificationList");
    const badge = document.getElementById("notificationBadge");
    if (!listContainer) return;

    try {
        const data = await api.getNotifications();
        listContainer.innerHTML = "";
        
        if (!data.notifications || data.notifications.length === 0) {
            listContainer.innerHTML = "<p class='no-notes'>No new notifications</p>";
            if (badge) badge.innerText = "0";
            return;
        }

        if (badge) badge.innerText = data.notifications.length;
        data.notifications.forEach(note => {
            const item = document.createElement("div");
            item.className = "notification-item";
            item.innerHTML = `<p>${note.message}</p>`;
            listContainer.appendChild(item);
        });
    } catch (err) {
        console.error("Failed to load notifications:", err);
    }
}

async function loadSplitInvitesUI() {
    const container = document.getElementById("invitesContainer");
    if (!container) return;

    try {
        const data = await api.getPendingInvites();
        container.innerHTML = "";

        if (!data.received || data.received.length === 0) {
            container.innerHTML = `<p class="no-invites">No pending roommate requests.</p>`;
            return;
        }

        data.received.forEach(invite => {
            const card = document.createElement("div");
            card.className = "invite-card";
            card.innerHTML = `
                <p><strong>${invite.sender_name}</strong> invited you to split rent for <strong>${invite.property_address}</strong>.</p>
                <p>Your Split Share: <strong>₦${invite.split_amount}</strong></p>
                <button onclick="handleInviteClick(${invite.id}, 'accept')" class="btn-accept">Accept</button>
                <button onclick="handleInviteClick(${invite.id}, 'decline')" class="btn-decline">Not Interested</button>
            `;
            container.appendChild(card);
        });
    } catch (err) {
        console.error("Error loading split invites:", err);
    }
}

window.handleInviteClick = async function(inviteId, action) {
    try {
        const result = await api.answerInvite(inviteId, action);
        if (result.success) {
            alert(`Invite ${action}ed successfully!`);
            loadSplitInvitesUI();
        }
    } catch (err) {
        console.error("Invite error:", err);
        alert("Failed to respond to invite.");
    }
};