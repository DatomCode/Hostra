const API_BASE_URL = 'http://127.0.0.1:8000';

function authHeader() {
    return { 'Authorization': `Bearer ${session.getToken()}` };
}

function handleAuthError(error) {
    if (error.message.includes('401') || error.message.includes('Unauthorized')) {
        session.clear();
        window.location.href = 'login.html';
    }
}

const api = {
    async login(email, password) {
        try {
            const response = await fetch(`${API_BASE_URL}/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });
            if (!response.ok) throw new Error('Login failed');
            return await response.json();
        } catch (error) { throw error; }
    },

    async signup(userData) {
        try {
            const formData = new FormData();
            for (const key in userData) {
                if (userData[key] !== null) formData.append(key, userData[key]);
            }
            const response = await fetch(`${API_BASE_URL}/auth/signup`, {
                method: 'POST',
                body: formData
            });
            if (!response.ok) throw new Error('Signup failed');
            return await response.json();
        } catch (error) { throw error; }
    },

    async logout() {
        session.clear();
        window.location.href = 'login.html';
        return { success: true };
    },

    async createListing(formData) {
        try {
            const response = await fetch(`${API_BASE_URL}/listings/`, {
                method: 'POST',
                headers: { ...authHeader() },
                body: formData
            });
            if (!response.ok) throw new Error('Listing creation failed');
            return await response.json();
        } catch (error) { handleAuthError(error); throw error; }
    },

    async getListings(filterMine = false) {
        try {
            const endpoint = filterMine ? `${API_BASE_URL}/listings/mine` : `${API_BASE_URL}/listings/`;
            const response = await fetch(endpoint, { headers: { ...authHeader() } });
            if (!response.ok) throw new Error('Failed to fetch listings');
            return await response.json();
        } catch (error) { handleAuthError(error); throw error; }
    },

    async getListing(listingId) {
        try {
            const response = await fetch(`${API_BASE_URL}/listings/${listingId}`, {
                headers: { ...authHeader() }
            });
            if (!response.ok) throw new Error('Failed to fetch listing details');
            return await response.json();
        } catch (error) { handleAuthError(error); throw error; }
    },

    async verifyListing(listingId, formData) {
        try {
            const response = await fetch(`${API_BASE_URL}/verify/${listingId}`, {
                method: 'POST',
                headers: { ...authHeader() },
                body: formData
            });
            if (!response.ok) throw new Error('Verification failed');
            return await response.json();
        } catch (error) { handleAuthError(error); throw error; }
    },

    async getVerifyFeed(showAll = false) {
        try {
            const url = showAll ? `${API_BASE_URL}/verify/feed?show_all=true` : `${API_BASE_URL}/verify/feed`;
            const response = await fetch(url, { headers: { ...authHeader() } });
            if (!response.ok) throw new Error('Failed to fetch feed');
            return await response.json();
        } catch (error) { handleAuthError(error); throw error; }
    },

    async getVerificationReport(listingId) {
        try {
            const response = await fetch(`${API_BASE_URL}/listings/${listingId}/verification-report`, {
                headers: { ...authHeader() }
            });
            if (!response.ok) throw new Error('Failed to fetch verification report');
            return await response.json();
        } catch (error) { handleAuthError(error); throw error; }
    },

    async submitReview(listingId, transcribedText, rating = null) {
        try {
            const response = await fetch(`${API_BASE_URL}/reviews/${listingId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', ...authHeader() },
                body: JSON.stringify({ transcribed_text: transcribedText, rating: rating })
            });
            if (!response.ok) throw new Error('Failed to submit review');
            return await response.json();
        } catch (error) { handleAuthError(error); throw error; }
    },

    async getReviews(listingId) {
        try {
            const response = await fetch(`${API_BASE_URL}/reviews/${listingId}`);
            if (!response.ok) throw new Error('Failed to fetch reviews');
            return await response.json();
        } catch (error) { throw error; }
    },

    async submitRoommateProfile(lifestyleNote) {
        try {
            const response = await fetch(`${API_BASE_URL}/roommate/profile`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', ...authHeader() },
                body: JSON.stringify({ lifestyle_note: lifestyleNote })
            });
            if (!response.ok) throw new Error('Failed to submit profile');
            return await response.json();
        } catch (error) { handleAuthError(error); throw error; }
    },

    async getRoommateMatches() {
        try {
            const response = await fetch(`${API_BASE_URL}/roommate/matches`, {
                headers: { ...authHeader() }
            });
            if (!response.ok) throw new Error('Failed to fetch matches');
            return await response.json();
        } catch (error) { handleAuthError(error); throw error; }
    },

    async getWallet() {
        try {
            const response = await fetch(`${API_BASE_URL}/wallet/me`, {
                headers: { ...authHeader() }
            });
            if (!response.ok) throw new Error('Failed to fetch wallet data');
            return await response.json();
        } catch (error) { handleAuthError(error); throw error; }
    },

    async withdrawWallet(amount) {
        try {
            const response = await fetch(`${API_BASE_URL}/wallet/withdraw`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', ...authHeader() },
                body: JSON.stringify({ amount: parseInt(amount) })
            });
            if (!response.ok) throw new Error('Failed to withdraw');
            return await response.json();
        } catch (error) { handleAuthError(error); throw error; }
    },

    async getUserProfile() {
        try {
            const response = await fetch(`${API_BASE_URL}/users/me`, {
                headers: { ...authHeader() }
            });
            if (!response.ok) throw new Error('Failed to fetch user profile');
            return await response.json();
        } catch (error) { handleAuthError(error); throw error; }
    },

    async updateUserProfile(area) {
        try {
            const response = await fetch(`${API_BASE_URL}/users/me`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json', ...authHeader() },
                body: JSON.stringify({ area })
            });
            if (!response.ok) throw new Error('Failed to update user profile');
            const data = await response.json();
            if (data.success && data.area !== undefined) {
                session.set(session.getToken(), session.getEmail(), session.getRole(), session.getName(), data.area);
            }
            return data;
        } catch (error) { handleAuthError(error); throw error; }
    },

    async uploadStudentID(formData) {
        try {
            const response = await fetch(`${API_BASE_URL}/users/verify-id`, {
                method: 'POST',
                headers: { ...authHeader() },
                body: formData
            });
            if (!response.ok) throw new Error('Failed to upload ID card');
            return await response.json();
        } catch (error) { handleAuthError(error); throw error; }
    },

    async payEscrow(listingId, split = false) {
        try {
            const response = await fetch(`${API_BASE_URL}/escrow/pay`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', ...authHeader() },
                body: JSON.stringify({ listing_id: listingId, is_split: split })
            });
            if (!response.ok) throw new Error('Failed to initiate payment');
            return await response.json();
        } catch (error) { handleAuthError(error); throw error; }
    },

    async confirmMoveIn(transactionId) {
        try {
            const response = await fetch(`${API_BASE_URL}/escrow/${transactionId}/confirm-move-in`, {
                method: 'POST',
                headers: { ...authHeader() }
            });
            if (!response.ok) throw new Error('Failed to confirm move in');
            return await response.json();
        } catch (error) { handleAuthError(error); throw error; }
    },

    async getEscrowForListing(listingId) {
        try {
            const response = await fetch(`${API_BASE_URL}/escrow/listing/${listingId}`, {
                headers: { ...authHeader() }
            });
            if (!response.ok) return { success: true, transaction: null };
            return await response.json();
        } catch (error) { return { success: true, transaction: null }; }
    },

    async sendSplitRentInvitation(roommateId, listingId) {
        try {
            const response = await fetch(`${API_BASE_URL}/escrow/split-invite`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', ...authHeader() },
                body: JSON.stringify({ roommate_id: roommateId, listing_id: listingId })
            });
            if (!response.ok) throw new Error('Failed to send invite');
            return await response.json();
        } catch (error) { handleAuthError(error); throw error; }
    },

    async getPendingInvites() {
        try {
            const response = await fetch(`${API_BASE_URL}/escrow/invites`, {
                headers: { ...authHeader() }
            });
            if (!response.ok) throw new Error('Failed to fetch invites');
            return await response.json();
        } catch (error) { handleAuthError(error); throw error; }
    },

    async answerInvite(inviteId, action) {
        try {
            const response = await fetch(`${API_BASE_URL}/escrow/invites/${inviteId}/answer`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', ...authHeader() },
                body: JSON.stringify({ action: action })
            });
            if (!response.ok) throw new Error('Failed to answer invite');
            return await response.json();
        } catch (error) { handleAuthError(error); throw error; }
    },

    async cancelInvite(inviteId) {
        try {
            const response = await fetch(`${API_BASE_URL}/escrow/invites/${inviteId}/cancel`, {
                method: 'POST',
                headers: { ...authHeader() }
            });
            if (!response.ok) throw new Error('Failed to cancel invite');
            return await response.json();
        } catch (error) { handleAuthError(error); throw error; }
    },

    async submitMaintenanceIssue(listingId, formData) {
        try {
            const response = await fetch(`${API_BASE_URL}/listings/${listingId}/maintenance`, {
                method: 'POST',
                headers: { ...authHeader() },
                body: formData
            });
            if (!response.ok) throw new Error('Failed to submit maintenance issue');
            return await response.json();
        } catch (error) { handleAuthError(error); throw error; }
    },

    async submitRepairAudit(listingId, formData) {
        try {
            const response = await fetch(`${API_BASE_URL}/listings/${listingId}/repair-audit`, {
                method: 'POST',
                headers: { ...authHeader() },
                body: formData
            });
            if (!response.ok) throw new Error('Repair audit failed');
            return await response.json();
        } catch (error) { handleAuthError(error); throw error; }
    },

    async getNotifications() {
        try {
            const response = await fetch(`${API_BASE_URL}/notifications`, {
                headers: { ...authHeader() }
            });
            if (!response.ok) throw new Error('Failed to fetch notifications');
            return await response.json();
        } catch (error) { handleAuthError(error); throw error; }
    }
};

const session = {
    set(token, email, role, name, area) {
        localStorage.setItem('hostra_token', token);
        localStorage.setItem('hostra_email', email);
        if (role) localStorage.setItem('hostra_role', role);
        if (name) localStorage.setItem('hostra_name', name);
        if (area) localStorage.setItem('hostra_area', area);
    },
    clear() {
        localStorage.removeItem('hostra_token');
        localStorage.removeItem('hostra_email');
        localStorage.removeItem('hostra_role');
        localStorage.removeItem('hostra_name');
        localStorage.removeItem('hostra_area');
    },
    isAuthenticated() { return !!localStorage.getItem('hostra_token'); },
    getToken() { return localStorage.getItem('hostra_token'); },
    getEmail() { return localStorage.getItem('hostra_email'); },
    getRole() { return localStorage.getItem('hostra_role') || 'student'; },
    getName() { return localStorage.getItem('hostra_name'); },
    getArea() { return localStorage.getItem('hostra_area'); }
};