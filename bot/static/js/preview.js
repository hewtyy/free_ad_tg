// Preview module - функции для работы с предпросмотром постов

// Загрузка предпросмотра поста
async function loadPostPreview() {
    console.log('loadPostPreview() called');
    const previewTextEl = document.getElementById('previewText');
    if (!previewTextEl) {
        console.error('previewText element not found');
        return;
    }
    console.log('previewText element found');
    
    try {
        const response = await window.safeFetch('/api/post/info');
        const data = await response.json();
        
        console.log('Post preview response:', response.ok, data);
        
        if (response.ok && data.success) {
            const post = data.post;
            console.log('Post preview: Post data received:', {
                hasText: !!post.text,
                textLength: post.text?.length,
                hasImage: !!post.image_url,
                useTemplate: post.use_template
            });
            
            // Обновляем текст
            previewTextEl.innerHTML = window.formatTelegramText(post.text || '');
            console.log('Post preview: Text updated');
            
            // Проверяем видимость вкладки предпросмотра
            const previewTab = previewTextEl.closest('.tab-pane');
            console.log('Post preview: Tab visibility:', {
                tabExists: !!previewTab,
                tabHasShow: previewTab?.classList.contains('show'),
                tabHasActive: previewTab?.classList.contains('active'),
                tabDisplay: previewTab ? window.getComputedStyle(previewTab).display : 'N/A',
                tabOpacity: previewTab ? window.getComputedStyle(previewTab).opacity : 'N/A'
            });
            
            // Обновляем изображение
            const previewImage = document.getElementById('previewImage');
            const previewImageElement = document.getElementById('previewImageElement');
            if (previewImage && previewImageElement) {
                if (post.image_url) {
                    previewImageElement.onload = function() {
                        // Показываем изображение только если оно успешно загрузилось
                        previewImage.style.display = 'block';
                        console.log('Post preview: Image loaded successfully');
                    };
                    previewImageElement.onerror = function() {
                        previewImage.style.display = 'none';
                        console.log('Post preview: Image failed to load');
                    };
                    previewImageElement.src = post.image_url;
                    previewImage.style.display = 'block';
                } else {
                    previewImage.style.display = 'none';
                    previewImageElement.src = '';
                    console.log('Post preview: No image to display');
                }
            }
            
            // Обновляем длину текста
            const previewTextLengthEl = document.getElementById('previewTextLength');
            if (previewTextLengthEl) {
                previewTextLengthEl.textContent = post.text_length || 0;
            }
            
            // Обновляем информацию о шаблоне
            const templateInfo = document.getElementById('previewTemplateInfo');
            const templateName = document.getElementById('previewTemplateName');
            if (post.use_template && post.template_name) {
                if (templateName) templateName.textContent = post.template_name;
                if (templateInfo) templateInfo.style.display = 'inline';
            } else {
                if (templateInfo) templateInfo.style.display = 'none';
            }
            
            // Обновляем время
            const previewTimeEl = document.getElementById('previewTime');
            if (previewTimeEl) {
                const now = new Date();
                previewTimeEl.textContent = now.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
            }
        } else {
            previewTextEl.innerHTML = '<span class="text-danger">' + (data.error || window.t('error.unknown')) + '</span>';
        }
    } catch (error) {
        console.error('Error loading post preview:', error);
        const previewTextEl = document.getElementById('previewText');
        if (previewTextEl) {
            previewTextEl.innerHTML = '<span class="text-danger">' + window.t('error.unknown') + '</span>';
        }
    }
}

// Обновление предпросмотра поста
async function updatePostPreview() {
    const chatSelect = document.getElementById('previewChatSelect');
    const selectedOption = chatSelect.options[chatSelect.selectedIndex];
    const chatId = selectedOption.value || '123456789';
    const chatTitle = selectedOption.text || 'Тестовая группа';
    
    try {
        const response = await window.safeFetch('/api/post/preview', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                chat_id: chatId,
                chat_title: chatTitle
            })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            const preview = data.preview;
            
            // Обновляем текст
            const previewTextEl = document.getElementById('previewText');
            if (previewTextEl) {
                previewTextEl.innerHTML = window.formatTelegramText(preview.text || '');
            }
            
            // Обновляем изображение
            const previewImage = document.getElementById('previewImage');
            const previewImageElement = document.getElementById('previewImageElement');
            if (previewImage && previewImageElement) {
                if (preview.image_url) {
                    previewImageElement.onload = function() {
                        // Показываем изображение только если оно успешно загрузилось
                        previewImage.style.display = 'block';
                    };
                    previewImageElement.onerror = function() {
                        previewImage.style.display = 'none';
                    };
                    previewImageElement.src = preview.image_url;
                } else {
                    previewImage.style.display = 'none';
                    previewImageElement.src = '';
                }
            }
            
            // Обновляем длину текста
            document.getElementById('previewTextLength').textContent = preview.text ? preview.text.length : 0;
            
            // Обновляем время
            const now = new Date();
            document.getElementById('previewTime').textContent = now.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
        } else {
            window.showToast(data.error || window.t('error.unknown'), 'error');
        }
    } catch (error) {
        window.showToast(window.t('error.unknown'), 'error');
    }
}

// Загрузка групп для предпросмотра
async function loadGroupsForPreview() {
    try {
        const response = await window.safeFetch('/api/groups');
        const data = await response.json();
        
        if (response.ok) {
            // API возвращает объект с ключом 'groups' или массив напрямую
            const groups = data.groups || (Array.isArray(data) ? data : []);
            const chatSelect = document.getElementById('previewChatSelect');
            
            if (!chatSelect) return;
            
            // Очищаем существующие опции (кроме первой)
            while (chatSelect.options.length > 1) {
                chatSelect.remove(1);
            }
            
            // Добавляем группы
            groups.forEach(group => {
                const option = document.createElement('option');
                option.value = group.id;
                option.textContent = group.title || group.id;
                option.setAttribute('data-title', group.title || '');
                chatSelect.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Ошибка загрузки групп для предпросмотра:', error);
    }
}

// Экспортируем функции в глобальную область видимости
window.loadPostPreview = loadPostPreview;
window.updatePostPreview = updatePostPreview;
window.loadGroupsForPreview = loadGroupsForPreview;

