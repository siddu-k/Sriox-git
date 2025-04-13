// Dashboard functionality for Sriox Platform

// Modals and Bootstrap components
const websiteModal = new bootstrap.Modal(document.getElementById('website-modal'));
const redirectModal = new bootstrap.Modal(document.getElementById('redirect-modal'));
const githubMappingModal = new bootstrap.Modal(document.getElementById('github-mapping-modal'));
const editWebsiteModal = new bootstrap.Modal(document.getElementById('edit-website-modal'));
const editRedirectModal = new bootstrap.Modal(document.getElementById('edit-redirect-modal'));
const editGithubMappingModal = new bootstrap.Modal(document.getElementById('edit-github-mapping-modal'));
const confirmDeleteModal = new bootstrap.Modal(document.getElementById('confirm-delete-modal'));

// Authentication & API helpers
const getAuthToken = () => localStorage.getItem('access_token');

const apiRequest = async (url, method = 'GET', data = null) => {
    const headers = {
        'Authorization': `Bearer ${getAuthToken()}`
    };

    if (data && !(data instanceof FormData)) {
        headers['Content-Type'] = 'application/json';
    }

    const config = {
        method,
        headers
    };

    if (data) {
        config.body = data instanceof FormData ? data : JSON.stringify(data);
    }

    const response = await fetch(url, config);

    if (response.status === 401) {
        // Token expired or invalid, redirect to login
        localStorage.removeItem('access_token');
        window.location.href = '/login';
        return null;
    }

    if (response.status === 204) { // No content response
        return { success: true };
    }

    const result = await response.json();

    if (!response.ok) {
        throw new Error(result.detail || 'API request failed');
    }

    return result;
};

// Date formatting helper
const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
};

// Check if user is authenticated
const checkAuth = () => {
    const token = getAuthToken();
    if (!token) {
        window.location.href = '/login';
    }
};

// Logout functionality
document.getElementById('logout-link').addEventListener('click', (e) => {
    e.preventDefault();
    localStorage.removeItem('access_token');
    window.location.href = '/login';
});

// Load dashboard data
const loadDashboardData = async () => {
    try {
        const data = await apiRequest('/dashboard');
        
        // Update resource counts
        document.getElementById('websites-count').textContent = data.resource_counts.websites;
        document.getElementById('redirects-count').textContent = data.resource_counts.redirects;
        document.getElementById('github-mappings-count').textContent = data.resource_counts.github_mappings;
        
        // Show/hide limit warnings
        document.getElementById('website-limit-reached').classList.toggle('d-none', data.resource_counts.websites < data.resource_counts.max_allowed);
        document.getElementById('add-website-btn').classList.toggle('d-none', data.resource_counts.websites >= data.resource_counts.max_allowed);
        
        document.getElementById('redirect-limit-reached').classList.toggle('d-none', data.resource_counts.redirects < data.resource_counts.max_allowed);
        document.getElementById('add-redirect-btn').classList.toggle('d-none', data.resource_counts.redirects >= data.resource_counts.max_allowed);
        
        document.getElementById('github-mapping-limit-reached').classList.toggle('d-none', data.resource_counts.github_mappings < data.resource_counts.max_allowed);
        document.getElementById('add-github-mapping-btn').classList.toggle('d-none', data.resource_counts.github_mappings >= data.resource_counts.max_allowed);
        
        // Populate websites table
        populateWebsitesTable(data.websites);
        
        // Populate redirects table
        populateRedirectsTable(data.redirects);
        
        // Populate GitHub mappings table
        populateGitHubMappingsTable(data.github_mappings);
        
        // Show dashboard content
        document.getElementById('loading-indicator').classList.add('d-none');
        document.getElementById('dashboard-content').classList.remove('d-none');
    } catch (error) {
        console.error('Failed to load dashboard data:', error);
        alert('Failed to load dashboard data. Please try again later.');
    }
};

// Populate websites table
const populateWebsitesTable = (websites) => {
    const tableBody = document.getElementById('websites-table-body');
    const noWebsitesMessage = document.getElementById('no-websites-message');
    
    // Clear existing content
    tableBody.innerHTML = '';
    
    if (websites.length === 0) {
        tableBody.parentElement.classList.add('d-none');
        noWebsitesMessage.classList.remove('d-none');
        return;
    }
    
    tableBody.parentElement.classList.remove('d-none');
    noWebsitesMessage.classList.add('d-none');
    
    websites.forEach(website => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${website.subdomain}</td>
            <td><a href="https://${website.subdomain}.sriox.com" target="_blank">${website.subdomain}.sriox.com</a></td>
            <td>${formatDate(website.created_at)}</td>
            <td>
                <div class="action-buttons">
                    <button class="btn btn-sm btn-outline-primary edit-website-btn" data-id="${website.id}" data-subdomain="${website.subdomain}">
                        <i class="bi bi-pencil"></i> Edit
                    </button>
                    <button class="btn btn-sm btn-outline-danger delete-website-btn" data-id="${website.id}">
                        <i class="bi bi-trash"></i> Delete
                    </button>
                </div>
            </td>
        `;
        tableBody.appendChild(row);
    });
    
    // Add event listeners for edit buttons
    document.querySelectorAll('.edit-website-btn').forEach(button => {
        button.addEventListener('click', function() {
            const id = this.dataset.id;
            const subdomain = this.dataset.subdomain;
            
            document.getElementById('edit-website-id').value = id;
            document.getElementById('edit-website-subdomain').value = subdomain;
            
            editWebsiteModal.show();
        });
    });
    
    // Add event listeners for delete buttons
    document.querySelectorAll('.delete-website-btn').forEach(button => {
        button.addEventListener('click', function() {
            const id = this.dataset.id;
            document.getElementById('delete-item-type').value = 'website';
            document.getElementById('delete-item-id').value = id;
            confirmDeleteModal.show();
        });
    });
};

// Populate redirects table
const populateRedirectsTable = (redirects) => {
    const tableBody = document.getElementById('redirects-table-body');
    const noRedirectsMessage = document.getElementById('no-redirects-message');
    
    // Clear existing content
    tableBody.innerHTML = '';
    
    if (redirects.length === 0) {
        tableBody.parentElement.classList.add('d-none');
        noRedirectsMessage.classList.remove('d-none');
        return;
    }
    
    tableBody.parentElement.classList.remove('d-none');
    noRedirectsMessage.classList.add('d-none');
    
    redirects.forEach(redirect => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${redirect.name}</td>
            <td><a href="https://sriox.com/${redirect.name}" target="_blank">sriox.com/${redirect.name}</a></td>
            <td><a href="${redirect.target_url}" target="_blank">${redirect.target_url}</a></td>
            <td>${formatDate(redirect.created_at)}</td>
            <td>
                <div class="action-buttons">
                    <button class="btn btn-sm btn-outline-primary edit-redirect-btn" 
                        data-id="${redirect.id}" 
                        data-name="${redirect.name}" 
                        data-url="${redirect.target_url}">
                        <i class="bi bi-pencil"></i> Edit
                    </button>
                    <button class="btn btn-sm btn-outline-danger delete-redirect-btn" data-id="${redirect.id}">
                        <i class="bi bi-trash"></i> Delete
                    </button>
                </div>
            </td>
        `;
        tableBody.appendChild(row);
    });
    
    // Add event listeners for edit buttons
    document.querySelectorAll('.edit-redirect-btn').forEach(button => {
        button.addEventListener('click', function() {
            const id = this.dataset.id;
            const name = this.dataset.name;
            const url = this.dataset.url;
            
            document.getElementById('edit-redirect-id').value = id;
            document.getElementById('edit-redirect-name').value = name;
            document.getElementById('edit-redirect-target-url').value = url;
            
            editRedirectModal.show();
        });
    });
    
    // Add event listeners for delete buttons
    document.querySelectorAll('.delete-redirect-btn').forEach(button => {
        button.addEventListener('click', function() {
            const id = this.dataset.id;
            document.getElementById('delete-item-type').value = 'redirect';
            document.getElementById('delete-item-id').value = id;
            confirmDeleteModal.show();
        });
    });
};

// Populate GitHub mappings table
const populateGitHubMappingsTable = (mappings) => {
    const tableBody = document.getElementById('github-mappings-table-body');
    const noMappingsMessage = document.getElementById('no-github-mappings-message');
    
    // Clear existing content
    tableBody.innerHTML = '';
    
    if (mappings.length === 0) {
        tableBody.parentElement.classList.add('d-none');
        noMappingsMessage.classList.remove('d-none');
        return;
    }
    
    tableBody.parentElement.classList.remove('d-none');
    noMappingsMessage.classList.add('d-none');
    
    mappings.forEach(mapping => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${mapping.subdomain}</td>
            <td>${mapping.github_username}</td>
            <td>${mapping.repository_name}</td>
            <td><a href="https://${mapping.subdomain}.sriox.com" target="_blank">${mapping.subdomain}.sriox.com</a></td>
            <td>${formatDate(mapping.created_at)}</td>
            <td>
                <div class="action-buttons">
                    <button class="btn btn-sm btn-outline-primary edit-github-mapping-btn" 
                        data-id="${mapping.id}" 
                        data-subdomain="${mapping.subdomain}" 
                        data-username="${mapping.github_username}" 
                        data-repo="${mapping.repository_name}">
                        <i class="bi bi-pencil"></i> Edit
                    </button>
                    <button class="btn btn-sm btn-outline-danger delete-github-mapping-btn" data-id="${mapping.id}">
                        <i class="bi bi-trash"></i> Delete
                    </button>
                </div>
            </td>
        `;
        tableBody.appendChild(row);
    });
    
    // Add event listeners for edit buttons
    document.querySelectorAll('.edit-github-mapping-btn').forEach(button => {
        button.addEventListener('click', function() {
            const id = this.dataset.id;
            const subdomain = this.dataset.subdomain;
            const username = this.dataset.username;
            const repo = this.dataset.repo;
            
            document.getElementById('edit-github-mapping-id').value = id;
            document.getElementById('edit-github-subdomain').value = subdomain;
            document.getElementById('edit-github-username').value = username;
            document.getElementById('edit-github-repository').value = repo;
            
            editGithubMappingModal.show();
        });
    });
    
    // Add event listeners for delete buttons
    document.querySelectorAll('.delete-github-mapping-btn').forEach(button => {
        button.addEventListener('click', function() {
            const id = this.dataset.id;
            document.getElementById('delete-item-type').value = 'github';
            document.getElementById('delete-item-id').value = id;
            confirmDeleteModal.show();
        });
    });
};

// Add Website Modal
document.getElementById('add-website-btn').addEventListener('click', () => {
    document.getElementById('website-form').reset();
    document.getElementById('website-modal-error').classList.add('d-none');
    websiteModal.show();
});

// Website Form Submit
document.getElementById('website-submit-btn').addEventListener('click', async () => {
    const subdomainInput = document.getElementById('website-subdomain');
    const fileInput = document.getElementById('website-zip');
    const errorElement = document.getElementById('website-modal-error');
    
    // Validate inputs
    if (!subdomainInput.value || !fileInput.files[0]) {
        errorElement.textContent = 'Both subdomain and ZIP file are required.';
        errorElement.classList.remove('d-none');
        return;
    }
    
    // Reset error message
    errorElement.classList.add('d-none');
    
    try {
        // Disable the button during upload
        const submitBtn = document.getElementById('website-submit-btn');
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Uploading...';
        
        // Create form data
        const formData = new FormData();
        formData.append('subdomain', subdomainInput.value);
        formData.append('zip_file', fileInput.files[0]);
        
        // Upload the website
        await apiRequest('/upload', 'POST', formData);
        
        // Hide modal and reload dashboard
        websiteModal.hide();
        loadDashboardData();
    } catch (error) {
        console.error('Website upload error:', error);
        errorElement.textContent = error.message;
        errorElement.classList.remove('d-none');
    } finally {
        // Re-enable the button
        const submitBtn = document.getElementById('website-submit-btn');
        submitBtn.disabled = false;
        submitBtn.innerHTML = 'Upload';
    }
});

// Edit Website Form Submit
document.getElementById('edit-website-submit-btn').addEventListener('click', async () => {
    const websiteId = document.getElementById('edit-website-id').value;
    const subdomain = document.getElementById('edit-website-subdomain').value;
    const errorElement = document.getElementById('edit-website-modal-error');
    
    // Validate inputs
    if (!subdomain) {
        errorElement.textContent = 'Subdomain is required.';
        errorElement.classList.remove('d-none');
        return;
    }
    
    // Reset error message
    errorElement.classList.add('d-none');
    
    try {
        // Disable the button during request
        const submitBtn = document.getElementById('edit-website-submit-btn');
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Updating...';
        
        // Update the website
        await apiRequest(`/upload/${websiteId}?subdomain=${subdomain}`, 'PUT');
        
        // Hide modal and reload dashboard
        editWebsiteModal.hide();
        loadDashboardData();
    } catch (error) {
        console.error('Website update error:', error);
        errorElement.textContent = error.message;
        errorElement.classList.remove('d-none');
    } finally {
        // Re-enable the button
        const submitBtn = document.getElementById('edit-website-submit-btn');
        submitBtn.disabled = false;
        submitBtn.innerHTML = 'Update';
    }
});

// Add Redirect Modal
document.getElementById('add-redirect-btn').addEventListener('click', () => {
    document.getElementById('redirect-form').reset();
    document.getElementById('redirect-modal-error').classList.add('d-none');
    redirectModal.show();
});

// Redirect Form Submit
document.getElementById('redirect-submit-btn').addEventListener('click', async () => {
    const nameInput = document.getElementById('redirect-name');
    const targetUrlInput = document.getElementById('redirect-target-url');
    const errorElement = document.getElementById('redirect-modal-error');
    
    // Validate inputs
    if (!nameInput.value || !targetUrlInput.value) {
        errorElement.textContent = 'Both name and target URL are required.';
        errorElement.classList.remove('d-none');
        return;
    }
    
    // Reset error message
    errorElement.classList.add('d-none');
    
    try {
        // Disable the button during request
        const submitBtn = document.getElementById('redirect-submit-btn');
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Creating...';
        
        // Create the redirect
        await apiRequest('/redirect', 'POST', {
            name: nameInput.value,
            target_url: targetUrlInput.value
        });
        
        // Hide modal and reload dashboard
        redirectModal.hide();
        loadDashboardData();
    } catch (error) {
        console.error('Redirect creation error:', error);
        errorElement.textContent = error.message;
        errorElement.classList.remove('d-none');
    } finally {
        // Re-enable the button
        const submitBtn = document.getElementById('redirect-submit-btn');
        submitBtn.disabled = false;
        submitBtn.innerHTML = 'Create';
    }
});

// Edit Redirect Form Submit
document.getElementById('edit-redirect-submit-btn').addEventListener('click', async () => {
    const redirectId = document.getElementById('edit-redirect-id').value;
    const name = document.getElementById('edit-redirect-name').value;
    const targetUrl = document.getElementById('edit-redirect-target-url').value;
    const errorElement = document.getElementById('edit-redirect-modal-error');
    
    // Validate inputs
    if (!name || !targetUrl) {
        errorElement.textContent = 'Both name and target URL are required.';
        errorElement.classList.remove('d-none');
        return;
    }
    
    // Reset error message
    errorElement.classList.add('d-none');
    
    try {
        // Disable the button during request
        const submitBtn = document.getElementById('edit-redirect-submit-btn');
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Updating...';
        
        // Update the redirect
        await apiRequest(`/redirect/${redirectId}`, 'PUT', {
            name: name,
            target_url: targetUrl
        });
        
        // Hide modal and reload dashboard
        editRedirectModal.hide();
        loadDashboardData();
    } catch (error) {
        console.error('Redirect update error:', error);
        errorElement.textContent = error.message;
        errorElement.classList.remove('d-none');
    } finally {
        // Re-enable the button
        const submitBtn = document.getElementById('edit-redirect-submit-btn');
        submitBtn.disabled = false;
        submitBtn.innerHTML = 'Update';
    }
});

// Add GitHub Mapping Modal
document.getElementById('add-github-mapping-btn').addEventListener('click', () => {
    document.getElementById('github-mapping-form').reset();
    document.getElementById('github-mapping-modal-error').classList.add('d-none');
    githubMappingModal.show();
});

// GitHub Mapping Form Submit
document.getElementById('github-mapping-submit-btn').addEventListener('click', async () => {
    const subdomainInput = document.getElementById('github-subdomain');
    const usernameInput = document.getElementById('github-username');
    const repoInput = document.getElementById('github-repository');
    const errorElement = document.getElementById('github-mapping-modal-error');
    
    // Validate inputs
    if (!subdomainInput.value || !usernameInput.value || !repoInput.value) {
        errorElement.textContent = 'Subdomain, GitHub username, and repository name are all required.';
        errorElement.classList.remove('d-none');
        return;
    }
    
    // Reset error message
    errorElement.classList.add('d-none');
    
    try {
        // Disable the button during request
        const submitBtn = document.getElementById('github-mapping-submit-btn');
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Creating...';
        
        // Create the GitHub mapping
        await apiRequest('/map-github', 'POST', {
            subdomain: subdomainInput.value,
            github_username: usernameInput.value,
            repository_name: repoInput.value
        });
        
        // Hide modal and reload dashboard
        githubMappingModal.hide();
        loadDashboardData();
    } catch (error) {
        console.error('GitHub mapping creation error:', error);
        errorElement.textContent = error.message;
        errorElement.classList.remove('d-none');
    } finally {
        // Re-enable the button
        const submitBtn = document.getElementById('github-mapping-submit-btn');
        submitBtn.disabled = false;
        submitBtn.innerHTML = 'Create';
    }
});

// Edit GitHub Mapping Form Submit
document.getElementById('edit-github-mapping-submit-btn').addEventListener('click', async () => {
    const mappingId = document.getElementById('edit-github-mapping-id').value;
    const subdomain = document.getElementById('edit-github-subdomain').value;
    const username = document.getElementById('edit-github-username').value;
    const repo = document.getElementById('edit-github-repository').value;
    const errorElement = document.getElementById('edit-github-mapping-modal-error');
    
    // Validate inputs
    if (!subdomain || !username || !repo) {
        errorElement.textContent = 'Subdomain, GitHub username, and repository name are all required.';
        errorElement.classList.remove('d-none');
        return;
    }
    
    // Reset error message
    errorElement.classList.add('d-none');
    
    try {
        // Disable the button during request
        const submitBtn = document.getElementById('edit-github-mapping-submit-btn');
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Updating...';
        
        // Update the GitHub mapping
        await apiRequest(`/map-github/${mappingId}`, 'PUT', {
            subdomain: subdomain,
            github_username: username,
            repository_name: repo
        });
        
        // Hide modal and reload dashboard
        editGithubMappingModal.hide();
        loadDashboardData();
    } catch (error) {
        console.error('GitHub mapping update error:', error);
        errorElement.textContent = error.message;
        errorElement.classList.remove('d-none');
    } finally {
        // Re-enable the button
        const submitBtn = document.getElementById('edit-github-mapping-submit-btn');
        submitBtn.disabled = false;
        submitBtn.innerHTML = 'Update';
    }
});

// Confirm Delete
document.getElementById('confirm-delete-btn').addEventListener('click', async () => {
    const itemType = document.getElementById('delete-item-type').value;
    const itemId = document.getElementById('delete-item-id').value;
    
    try {
        // Disable the button during request
        const deleteBtn = document.getElementById('confirm-delete-btn');
        deleteBtn.disabled = true;
        deleteBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Deleting...';
        
        // Delete the item based on its type
        let endpoint;
        switch (itemType) {
            case 'website':
                endpoint = `/upload/${itemId}`;
                break;
            case 'redirect':
                endpoint = `/redirect/${itemId}`;
                break;
            case 'github':
                endpoint = `/map-github/${itemId}`;
                break;
            default:
                throw new Error('Unknown item type');
        }
        
        await apiRequest(endpoint, 'DELETE');
        
        // Hide modal and reload dashboard
        confirmDeleteModal.hide();
        loadDashboardData();
    } catch (error) {
        console.error('Delete error:', error);
        alert(`Error deleting item: ${error.message}`);
    } finally {
        // Re-enable the button
        const deleteBtn = document.getElementById('confirm-delete-btn');
        deleteBtn.disabled = false;
        deleteBtn.innerHTML = 'Delete';
    }
});

// Initialize dashboard if we're on the dashboard page
if (window.location.pathname === '/dashboard') {
    checkAuth();
    loadDashboardData();
}