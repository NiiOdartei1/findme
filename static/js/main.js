document.addEventListener('DOMContentLoaded', () => {
  const chips = document.querySelectorAll('.chip-row span');
  chips.forEach((chip) => {
    chip.addEventListener('click', () => {
      chip.classList.toggle('selected');
    });
  });

  const thumbnailImages = document.querySelectorAll('.thumbnail-row img');
  const mainImage = document.querySelector('.main-image img');

  if (mainImage && thumbnailImages.length) {
    thumbnailImages.forEach((thumb) => {
      thumb.addEventListener('click', () => {
        mainImage.src = thumb.src;
      });
    });
  }
});
