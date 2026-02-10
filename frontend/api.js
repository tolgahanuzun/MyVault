// API Service
const API = {
    async request(endpoint, options = {}) {
        const url = `${Config.API_BASE_URL}${endpoint}`;
        
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        if (Auth && Auth.isAuthenticated()) {
            const authHeaders = Auth.getHeaders();
            Object.assign(headers, authHeaders);
        }

        const config = {
            ...options,
            headers
        };

        try {
            const response = await fetch(url, config);
            
            // Handle 401 Unauthorized globally
            if (response.status === 401) {
                if (Auth) Auth.handleUnauthorized();
                throw new Error("Unauthorized");
            }

            const data = await response.json();
            
            if (!response.ok) {
                // Return structured error
                throw {
                    status: response.status,
                    message: data.detail || 'An error occurred',
                    data: data
                };
            }

            return data;
        } catch (error) {
            // Re-throw structured errors, wrap network errors
            if (error.status) {
                throw error;
            } else {
                 console.error("API Request Error:", error);
                 throw {
                     status: 0,
                     message: "Network error or server unreachable",
                     originalError: error
                 };
            }
        }
    },

    async get(endpoint) {
        return this.request(endpoint, { method: 'GET' });
    },

    async post(endpoint, body) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(body)
        });
    },

    async put(endpoint, body) {
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(body)
        });
    },

    async delete(endpoint) {
        return this.request(endpoint, { method: 'DELETE' });
    }
};

window.API = API;
