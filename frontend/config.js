// Configuration
const Config = {
    API_BASE_URL: "http://localhost:8000", // Empty for same origin, or e.g. "http://localhost:8000"
    ENDPOINTS: {
        LOGIN: '/auth/login',
        REGISTER: '/auth/register',
        ME: '/auth/me',
        CHANGE_PASSWORD: '/auth/me/password',
        PORTFOLIO: '/portfolio/',
        ASSETS: '/assets/',
        TRANSACTION: '/portfolio/transaction',
        SEARCH: '/assets/search'
    }
};

window.Config = Config;
