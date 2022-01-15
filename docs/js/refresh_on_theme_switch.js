const ref = document.querySelector("[data-md-component=palette]")
component$.subscribe(component => {
    if (component.ref === ref) {
        location.reload()
    }
})
