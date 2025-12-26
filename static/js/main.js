/**
 * ===================================
 * Zenvexa API Platform - Main Script
 * Version: 1.0.0
 * Pure Vanilla JavaScript
 * ===================================
 */

(function() {
    'use strict';

    // ===================================
    // Mobile Menu Toggle
    // ===================================
    const initMobileMenu = () => {
        const mobileMenuBtn = document.querySelector('.mobile-menu');
        const navLinks = document.querySelector('.nav-links');

        if (mobileMenuBtn && navLinks) {
            mobileMenuBtn.addEventListener('click', () => {
                navLinks.classList.toggle('active');
                mobileMenuBtn.textContent = navLinks.classList.contains('active') ? '✕' : '☰';
            });

            // Close menu when clicking outside
            document.addEventListener('click', (e) => {
                if (!e.target.closest('nav')) {
                    navLinks.classList.remove('active');
                    mobileMenuBtn.textContent = '☰';
                }
            });

            // Close menu when clicking on a link
            const menuLinks = navLinks.querySelectorAll('a');
            menuLinks.forEach(link => {
                link.addEventListener('click', () => {
                    navLinks.classList.remove('active');
                    mobileMenuBtn.textContent = '☰';
                });
            });
        }
    };

    // ===================================
    // Smooth Scrolling for Internal Links
    // ===================================
    const initSmoothScrolling = () => {
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function(e) {
                const href = this.getAttribute('href');
                
                // Skip if it's just "#"
                if (href === '#') return;

                e.preventDefault();
                const target = document.querySelector(href);

                if (target) {
                    const headerOffset = 80;
                    const elementPosition = target.getBoundingClientRect().top;
                    const offsetPosition = elementPosition + window.pageYOffset - headerOffset;

                    window.scrollTo({
                        top: offsetPosition,
                        behavior: 'smooth'
                    });
                }
            });
        });
    };

    // ===================================
    // Form Validation
    // ===================================
    const validateEmail = (email) => {
        const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return re.test(email);
    };

    const validatePassword = (password) => {
        return password.length >= 8;
    };

    const showError = (input, message) => {
        const formGroup = input.closest('.form-group');
        const errorElement = formGroup.querySelector('.error-message');
        
        input.classList.add('error');
        input.classList.remove('success');
        
        if (errorElement) {
            errorElement.textContent = message;
            errorElement.classList.add('show');
        }
    };

    const showSuccess = (input) => {
        const formGroup = input.closest('.form-group');
        const errorElement = formGroup.querySelector('.error-message');
        
        input.classList.remove('error');
        input.classList.add('success');
        
        if (errorElement) {
            errorElement.classList.remove('show');
        }
    };

    const clearValidation = (input) => {
        const formGroup = input.closest('.form-group');
        const errorElement = formGroup.querySelector('.error-message');
        
        input.classList.remove('error', 'success');
        
        if (errorElement) {
            errorElement.classList.remove('show');
        }
    };

    // ===================================
    // Contact Form Validation
    // ===================================
    const initContactForm = () => {
        const contactForm = document.getElementById('contactForm');
        
        if (contactForm) {
            contactForm.addEventListener('submit', (e) => {
                e.preventDefault();
                let isValid = true;

                const name = document.getElementById('name');
                const email = document.getElementById('email');
                const subject = document.getElementById('subject');
                const message = document.getElementById('message');

                // Validate name
                if (name && name.value.trim() === '') {
                    showError(name, 'Name is required');
                    isValid = false;
                } else if (name) {
                    showSuccess(name);
                }

                // Validate email
                if (email && email.value.trim() === '') {
                    showError(email, 'Email is required');
                    isValid = false;
                } else if (email && !validateEmail(email.value)) {
                    showError(email, 'Please enter a valid email');
                    isValid = false;
                } else if (email) {
                    showSuccess(email);
                }

                // Validate subject
                if (subject && subject.value === '') {
                    showError(subject, 'Please select a subject');
                    isValid = false;
                } else if (subject) {
                    showSuccess(subject);
                }

                // Validate message
                if (message && message.value.trim() === '') {
                    showError(message, 'Message is required');
                    isValid = false;
                } else if (message && message.value.trim().length < 10) {
                    showError(message, 'Message must be at least 10 characters');
                    isValid = false;
                } else if (message) {
                    showSuccess(message);
                }

                if (isValid) {
                    showAlert('success', 'Thank you! Your message has been sent successfully.');
                    contactForm.reset();
                    
                    // Clear validation states
                    contactForm.querySelectorAll('input, textarea, select').forEach(input => {
                        clearValidation(input);
                    });
                }
            });
        }
    };

    // ===================================
    // Login Form Validation
    // ===================================
    const initLoginForm = () => {
        const loginForm = document.getElementById('login-form');
        
        if (loginForm) {
            loginForm.addEventListener('submit', (e) => {
                e.preventDefault();
                let isValid = true;

                const email = document.getElementById('login-email');
                const password = document.getElementById('login-password');

                // Validate email
                if (email.value.trim() === '') {
                    showError(email, 'Email is required');
                    isValid = false;
                } else if (!validateEmail(email.value)) {
                    showError(email, 'Please enter a valid email');
                    isValid = false;
                } else {
                    showSuccess(email);
                }

                // Validate password
                if (password.value.trim() === '') {
                    showError(password, 'Password is required');
                    isValid = false;
                } else {
                    showSuccess(password);
                }

                if (isValid) {
                    showAlert('info', 'Login functionality would be handled by your backend.');
                }
            });
        }
    };

    // ===================================
    // Signup Form Validation
    // ===================================
    const initSignupForm = () => {
        const signupForm = document.getElementById('signup-form');
        
        if (signupForm) {
            signupForm.addEventListener('submit', (e) => {
                e.preventDefault();
                let isValid = true;

                const name = document.getElementById('signup-name');
                const email = document.getElementById('signup-email');
                const password = document.getElementById('signup-password');
                const confirm = document.getElementById('signup-confirm');

                // Validate name
                if (name.value.trim() === '') {
                    showError(name, 'Name is required');
                    isValid = false;
                } else {
                    showSuccess(name);
                }

                // Validate email
                if (email.value.trim() === '') {
                    showError(email, 'Email is required');
                    isValid = false;
                } else if (!validateEmail(email.value)) {
                    showError(email, 'Please enter a valid email');
                    isValid = false;
                } else {
                    showSuccess(email);
                }

                // Validate password
                if (password.value.trim() === '') {
                    showError(password, 'Password is required');
                    isValid = false;
                } else if (!validatePassword(password.value)) {
                    showError(password, 'Password must be at least 8 characters');
                    isValid = false;
                } else {
                    showSuccess(password);
                }

                // Validate confirm password
                if (confirm.value.trim() === '') {
                    showError(confirm, 'Please confirm your password');
                    isValid = false;
                } else if (password.value !== confirm.value) {
                    showError(confirm, 'Passwords do not match');
                    isValid = false;
                } else {
                    showSuccess(confirm);
                }

                if (isValid) {
                    showAlert('success', 'Account created successfully!');
                    signupForm.reset();
                }
            });

            // Real-time password strength indicator
            const passwordInput = document.getElementById('signup-password');
            if (passwordInput) {
                passwordInput.addEventListener('input', () => {
                    updatePasswordStrength(passwordInput.value);
                });
            }
        }
    };

    // ===================================
    // Password Strength Indicator
    // ===================================
    const updatePasswordStrength = (password) => {
        const strengthBar = document.getElementById('password-strength-bar');
        const strengthContainer = document.getElementById('password-strength');

        if (!strengthBar || !strengthContainer) return;

        if (password.length === 0) {
            strengthContainer.classList.remove('show');
            return;
        }

        strengthContainer.classList.add('show');

        let strength = 0;
        if (password.length >= 8) strength++;
        if (password.match(/[a-z]/) && password.match(/[A-Z]/)) strength++;
        if (password.match(/[0-9]/)) strength++;
        if (password.match(/[^a-zA-Z0-9]/)) strength++;

        strengthBar.className = 'password-strength-bar';
        if (strength <= 1) {
            strengthBar.classList.add('strength-weak');
        } else if (strength <= 3) {
            strengthBar.classList.add('strength-medium');
        } else {
            strengthBar.classList.add('strength-strong');
        }
    };

    // ===================================
    // Copy to Clipboard
    // ===================================
    const initCopyButtons = () => {
        document.querySelectorAll('[data-copy]').forEach(button => {
            button.addEventListener('click', () => {
                const textToCopy = button.getAttribute('data-copy');
                
                if (navigator.clipboard && window.isSecureContext) {
                    navigator.clipboard.writeText(textToCopy).then(() => {
                        showAlert('success', 'Copied to clipboard!');
                    }).catch(() => {
                        fallbackCopy(textToCopy);
                    });
                } else {
                    fallbackCopy(textToCopy);
                }
            });
        });

        // Auto-copy for copy buttons in key items
        document.querySelectorAll('.btn-secondary').forEach(button => {
            if (button.textContent.trim() === 'Copy') {
                button.addEventListener('click', (e) => {
                    const keyItem = button.closest('.key-item');
                    if (keyItem) {
                        const keyValue = keyItem.querySelector('.key-value');
                        if (keyValue) {
                            const text = keyValue.textContent.trim();
                            copyToClipboard(text, button);
                        }
                    }
                });
            }
        });
    };

    const copyToClipboard = (text, button) => {
        if (navigator.clipboard && window.isSecureContext) {
            navigator.clipboard.writeText(text).then(() => {
                const originalText = button.textContent;
                button.textContent = 'Copied!';
                setTimeout(() => {
                    button.textContent = originalText;
                }, 2000);
            }).catch(() => {
                fallbackCopy(text);
            });
        } else {
            fallbackCopy(text);
        }
    };

    const fallbackCopy = (text) => {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        document.body.appendChild(textArea);
        textArea.select();
        
        try {
            document.execCommand('copy');
            showAlert('success', 'Copied to clipboard!');
        } catch (err) {
            showAlert('error', 'Failed to copy');
        }
        
        document.body.removeChild(textArea);
    };

    // ===================================
    // Alert System
    // ===================================
    const showAlert = (type, message) => {
        // Remove existing alerts
        const existingAlerts = document.querySelectorAll('.custom-alert');
        existingAlerts.forEach(alert => alert.remove());

        const alert = document.createElement('div');
        alert.className = `custom-alert alert-${type}`;
        alert.innerHTML = `
            <span>${message}</span>
            <button class="alert-close">&times;</button>
        `;

        alert.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 1rem 1.5rem;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 10000;
            display: flex;
            align-items: center;
            gap: 1rem;
            animation: slideInRight 0.3s ease-out;
            max-width: 400px;
        `;

        if (type === 'success') {
            alert.style.background = '#dcfce7';
            alert.style.color = '#166534';
            alert.style.border = '1px solid #10b981';
        } else if (type === 'error') {
            alert.style.background = '#fee2e2';
            alert.style.color = '#991b1b';
            alert.style.border = '1px solid #ef4444';
        } else if (type === 'info') {
            alert.style.background = '#eff6ff';
            alert.style.color = '#1e40af';
            alert.style.border = '1px solid #3b82f6';
        }

        document.body.appendChild(alert);

        const closeBtn = alert.querySelector('.alert-close');
        closeBtn.style.cssText = `
            background: none;
            border: none;
            font-size: 1.5rem;
            cursor: pointer;
            color: inherit;
            opacity: 0.7;
        `;

        closeBtn.addEventListener('click', () => {
            alert.remove();
        });

        setTimeout(() => {
            alert.remove();
        }, 5000);
    };

    // ===================================
    // Active Nav Link Highlighting
    // ===================================
    const highlightActiveNav = () => {
        const currentPath = window.location.pathname;
        const navLinks = document.querySelectorAll('.nav-links a');

        navLinks.forEach(link => {
            const linkPath = new URL(link.href).pathname;
            if (linkPath === currentPath) {
                link.classList.add('active');
            }
        });
    };

    // ===================================
    // Input Clear on Focus (Optional)
    // ===================================
    const initInputClearOnFocus = () => {
        document.querySelectorAll('input, textarea').forEach(input => {
            input.addEventListener('focus', () => {
                clearValidation(input);
            });
        });
    };

    // ===================================
    // Scroll to Top Button
    // ===================================
    const initScrollToTop = () => {
        const scrollBtn = document.createElement('button');
        scrollBtn.innerHTML = '↑';
        scrollBtn.className = 'scroll-to-top';
        scrollBtn.style.cssText = `
            position: fixed;
            bottom: 30px;
            right: 30px;
            width: 50px;
            height: 50px;
            border-radius: 50%;
            background: var(--accent-color);
            color: white;
            border: none;
            font-size: 1.5rem;
            cursor: pointer;
            opacity: 0;
            visibility: hidden;
            transition: all 0.3s ease;
            z-index: 1000;
            box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);
        `;

        document.body.appendChild(scrollBtn);

        window.addEventListener('scroll', () => {
            if (window.pageYOffset > 300) {
                scrollBtn.style.opacity = '1';
                scrollBtn.style.visibility = 'visible';
            } else {
                scrollBtn.style.opacity = '0';
                scrollBtn.style.visibility = 'hidden';
            }
        });

        scrollBtn.addEventListener('click', () => {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });
    };

    // ===================================
    // Initialize All Functions
    // ===================================
    const init = () => {
        initMobileMenu();
        initSmoothScrolling();
        initContactForm();
        initLoginForm();
        initSignupForm();
        initCopyButtons();
        highlightActiveNav();
        initInputClearOnFocus();
        initScrollToTop();
    };

    // Run when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
