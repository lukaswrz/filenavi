'use strict';

document.addEventListener('DOMContentLoaded', () => {
    let form = document.querySelector('form.upload-files');

    form.querySelector('button[type="submit"]').style.display = 'none';
    form.querySelector('input[type="file"]').addEventListener('change', () => {
        form.submit();
    });
});
