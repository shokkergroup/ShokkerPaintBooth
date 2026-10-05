/* Range controls keep focus/capture while dragging; re-order only after release. */
(function () {
    'use strict';
    window.SPBPickerDetail = {
        refreshFavorite: function (id, favorite) {
            const popup = document.getElementById('swatchPopup');
            if (!popup || !popup.classList.contains('active')) return false;
            popup.querySelectorAll('.swatch-item[data-finish-id]').forEach(card => {
                if (card.dataset.finishId !== id) return;
                const button = card.querySelector('.swatch-fav-btn');
                if (button) {
                    button.classList.toggle('active', favorite);
                    button.textContent = favorite ? '★' : '☆';
                    button.title = favorite ? 'Remove from favorites' : 'Add to favorites';
                }
                if (!favorite && card.closest('.swatch-favorites-group')) card.remove();
            });
            if (typeof swatchPopupState !== 'undefined' && swatchPopupState.filter === 'favorites' &&
                typeof filterSwatchPopup === 'function') {
                filterSwatchPopup(document.getElementById('swatchSearchInput')?.value || '');
            }
            return true;
        }
    };
    document.addEventListener('keydown', function (event) {
        if (event.target.matches('.swatch-rate-slider')) event.stopPropagation();
    }, true);
    document.addEventListener('input', function (event) {
        if (!event.target.matches('.swatch-rate-slider')) return;
        const slider = event.target;
        slider.style.setProperty('--rating-fill', slider.value + '%');
        const card = slider.closest('.swatch-item');
        if (card) document.querySelectorAll('#swatchPopup .swatch-item').forEach(other => {
            if (other !== card && other.dataset.finishId === card.dataset.finishId) {
                other.dataset.rating = slider.value;
                const input = other.querySelector('.swatch-rate-slider');
                const output = other.querySelector('.swatch-rate-val');
                if (input) input.value = slider.value;
                if (output) output.textContent = slider.value;
            }
        });
    });
    document.addEventListener('change', function (event) {
        if (!event.target.matches('.swatch-rate-slider')) return;
        // Defer DOM moves until the release/click sequence is complete.
        setTimeout(function () {
            if (typeof _applySwatchPopupSort === 'function') _applySwatchPopupSort(document.getElementById('swatchPopupGrid'));
        }, 0);
    });
})();
