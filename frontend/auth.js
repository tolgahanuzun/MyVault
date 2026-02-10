const Auth = {
    tokenKey: 'auth_token',
    
    // Login
    async login(username, password) {
        try {
            const response = await fetch(`${Config.API_BASE_URL}${Config.ENDPOINTS.LOGIN}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username, password })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                localStorage.setItem(this.tokenKey, data.access_token);
                return { success: true };
            } else {
                return { success: false, message: data.detail || 'Login failed' };
            }
        } catch (error) {
            console.error('Login error:', error);
            return { success: false, message: 'Network error' };
        }
    },
    
    // Register
    async register(username, password, fullName) {
        // Validation
        if (!this.validatePassword(password)) {
            return { 
                success: false, 
                message: 'Password must be at least 8 characters long and contain uppercase, lowercase letters and numbers.' 
            };
        }

        try {
            const response = await fetch(`${Config.API_BASE_URL}${Config.ENDPOINTS.REGISTER}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ 
                    username, 
                    password, 
                    full_name: fullName 
                })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                localStorage.setItem(this.tokenKey, data.access_token);
                return { success: true };
            } else {
                return { success: false, message: data.detail || 'Registration failed' };
            }
        } catch (error) {
            console.error('Register error:', error);
            return { success: false, message: 'Network error' };
        }
    },
    
    // Logout
    logout() {
        localStorage.removeItem(this.tokenKey);
        window.location.href = '/static/login.html';
    },
    
    // Get Token
    getToken() {
        return localStorage.getItem(this.tokenKey);
    },
    
    // Check if authenticated
    isAuthenticated() {
        return !!this.getToken();
    },
    
    // Require Auth (Redirect if not)
    requireAuth() {
        if (!this.isAuthenticated()) {
            window.location.href = '/static/login.html';
            return false;
        }
        return true;
    },
    
    // Get Auth Headers
    getHeaders() {
        const token = this.getToken();
        return {
            'Content-Type': 'application/json',
            'Authorization': token ? `Bearer ${token}` : ''
        };
    },
    
    // Handle 401
    handleUnauthorized() {
        this.logout();
    },

    // Validation Helper
    validatePassword(password) {
        if (password.length < 8) return false;
        if (!/[A-Z]/.test(password)) return false;
        if (!/[a-z]/.test(password)) return false;
        if (!/[0-9]/.test(password)) return false;
        return true;
    }
};

window.Auth = Auth;
