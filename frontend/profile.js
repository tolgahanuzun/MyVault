document.addEventListener('DOMContentLoaded', async () => {
    // Check authentication using the central Auth module
    if (!Auth.requireAuth()) {
        return;
    }

    // DOM Elements
    const usernameInput = document.getElementById('username');
    const fullNameInput = document.getElementById('fullName');
    const avatarImage = document.getElementById('avatarImage');
    const avatarInput = document.getElementById('avatarInput');
    const uploadAvatarBtn = document.getElementById('uploadAvatarBtn');
    const profileForm = document.getElementById('profileForm');
    const passwordForm = document.getElementById('passwordForm');
    const logoutBtn = document.getElementById('logoutBtn');

    // Toast function
    const showToast = (message, isError = false) => {
        const toastEl = document.getElementById('liveToast');
        const toastTitle = document.getElementById('toastTitle');
        const toastMessage = document.getElementById('toastMessage');
        
        toastTitle.textContent = isError ? 'Hata' : 'Başarılı';
        toastTitle.className = isError ? 'me-auto text-danger' : 'me-auto text-success';
        toastMessage.textContent = message;
        
        const toast = new bootstrap.Toast(toastEl);
        toast.show();
    };

    // Load User Data
    try {
        const user = await API.get(Config.ENDPOINTS.ME);
        
        usernameInput.value = user.username;
        fullNameInput.value = user.full_name || '';
        if (user.avatar_url) {
            avatarImage.src = user.avatar_url;
        }
    } catch (error) {
        console.error(error);
        showToast('Kullanıcı bilgileri yüklenirken hata oluştu', true);
    }

    // Update Profile Info
    profileForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        try {
            await API.put(Config.ENDPOINTS.ME, {
                full_name: fullNameInput.value
            });
            
            showToast('Profil bilgileri güncellendi');
        } catch (error) {
            console.error(error);
            showToast('Güncelleme sırasında hata oluştu', true);
        }
    });

    // Avatar Selection & Preview
    avatarInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                avatarImage.src = e.target.result;
            };
            reader.readAsDataURL(file);
            uploadAvatarBtn.disabled = false;
        }
    });

    // Upload Avatar
    uploadAvatarBtn.addEventListener('click', async () => {
        const file = avatarInput.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);

        try {
            const headers = Auth.getHeaders();
            delete headers['Content-Type']; // Let browser set Content-Type with boundary for FormData

            const response = await fetch(`${Config.API_BASE_URL}/auth/me/avatar`, {
                method: 'POST',
                headers: headers,
                body: formData
            });

            if (response.status === 401) {
                Auth.handleUnauthorized();
                return;
            }

            if (!response.ok) throw new Error('Fotoğraf yüklenemedi');

            const updatedUser = await response.json();

            avatarImage.src = updatedUser.avatar_url;
            showToast('Profil fotoğrafı güncellendi');
            uploadAvatarBtn.disabled = true;
            avatarInput.value = '';
        } catch (error) {
            console.error(error);
            showToast('Fotoğraf yüklenirken hata oluştu', true);
        }
    });

    // Change Password
    passwordForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const currentPassword = document.getElementById('currentPassword').value;
        const newPassword = document.getElementById('newPassword').value;
        const confirmPassword = document.getElementById('confirmPassword').value;

        if (newPassword !== confirmPassword) {
            showToast('Yeni şifreler eşleşmiyor', true);
            return;
        }

        try {
            await API.post(Config.ENDPOINTS.CHANGE_PASSWORD, {
                current_password: currentPassword,
                new_password: newPassword
            });

            showToast('Şifre başarıyla değiştirildi');
            passwordForm.reset();
        } catch (error) {
            console.error(error);
            // API throws structured error, error.message is from backend or default
            showToast(error.message || 'Şifre değiştirilemedi', true);
        }
    });

    // Logout
    logoutBtn.addEventListener('click', () => {
        Auth.logout();
    });
});
