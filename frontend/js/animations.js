document.addEventListener('DOMContentLoaded', () => {
    
    // Check for reduced motion
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // 1. Reveal Animations
    const revealObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('reveal-visible');
                observer.unobserve(entry.target);
            }
        });
    }, {
        root: null,
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    });

    document.querySelectorAll('.reveal-item').forEach((item) => {
        item.classList.add('reveal-hidden');
        revealObserver.observe(item);
    });

    // 2. Count Up Stats
    if (!prefersReducedMotion) {
        const countObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    startCounting(entry.target);
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.5 });

        document.querySelectorAll('.count-up').forEach(item => {
            countObserver.observe(item);
        });

        function startCounting(el) {
            const target = parseInt(el.getAttribute('data-count'), 10);
            if (isNaN(target)) return;
            
            const duration = 1500; 
            const startTime = performance.now();
            
            const textContent = el.innerText;
            const hasPlus = textContent.includes('+');
            const hasNaira = textContent.includes('₦');

            function updateCounter(currentTime) {
                const elapsed = currentTime - startTime;
                const progress = Math.min(elapsed / duration, 1);
                
                const easeOut = progress * (2 - progress);
                const currentVal = Math.floor(easeOut * target);

                let displayVal = currentVal;
                if (hasNaira) displayVal = '₦' + displayVal;
                if (hasPlus) displayVal = displayVal + '+';
                
                el.innerText = displayVal;

                if (progress < 1) {
                    requestAnimationFrame(updateCounter);
                } else {
                    let finalVal = target;
                    if (hasNaira) finalVal = '₦' + finalVal;
                    if (hasPlus) finalVal = finalVal + '+';
                    el.innerText = finalVal;
                }
            }
            requestAnimationFrame(updateCounter);
        }
    }

    // 3. Seal Stamp Animation
    if (!prefersReducedMotion) {
        const sealObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animate-stamp');
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.2, rootMargin: '0px 0px -20px 0px' });

        document.querySelectorAll('.verified-seal').forEach(seal => {
            // hide before animation
            seal.style.opacity = '0';
            sealObserver.observe(seal);
        });
    }

    // 4. Parallax Floating Search
    if (!prefersReducedMotion) {
        const searchContainer = document.querySelector('.floating-search-container');
        if (searchContainer) {
            window.addEventListener('scroll', () => {
                const scrolled = window.pageYOffset;
                // Move slightly slower than scroll (parallax)
                searchContainer.style.transform = `translateY(${scrolled * 0.15}px)`;
            });
        }
    }
});
