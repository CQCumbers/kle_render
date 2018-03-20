# KLE-Render
Get prettier images of Keyboard Layout Editor designs

This project uses Pillow (Python Image Library), Flask, and Flask-RESTPlus to serve up 'renders' of keyboards from their keyboard layout editor JSON, by stretching, tinting, and tiling base images of a 1u keycap.

Check it out at [kle-render.herokuapp.com](http://kle-render.herokuapp.com/).

You can also see a [sample render](#sample-image) of Nantucket Selectric here.

## Frequently Asked Questions
I've also answered many common questions on the [reddit post](http://www.reddit.com/r/MechanicalKeyboards/6cvk61). If you have a simple question not answered here, try [messaging me](https://www.reddit.com/user/CQ_Cumbers/) on reddit.

### What keycap profiles are supported?
KLE-Render technically only supports SA and GMK keycap profiles, but most layouts for DSA, DCS, OEM, or even beamspring profiles should still look pretty close. Keycap row profiles (like SA R1) are not supported - everything key is assumed to be uniform row 3.

### Why am I getting an internal server error when I try to render a layout?
It's quite possible the server is overloaded, but also possible that something in your layout is causing the server to crash. If you're uploading JSON, make sure it is downloaded via the button. If as far as you can tell everything is inputted correctly, please contact me with the gist link or JSON that is causing the error and I will try to fix the problem.

### Why are the edges cut off on my image?
To save time, the program guesses a reasonable initial image size given the number of keys in the layout, then crops it to size after rendering all of the keys. For certain narrow layouts, the initial guess may be too small in one dimension, causing the final image to be cut off. I will try to fix this issue when possible, but for now try adding extra keys to make the layout more square, then cropping the render afterwards.

### Can I render from a different angle? What if I need to render with a case, or rare profiles, or translucent keycaps?
This tool can generate relatively realistic renders of arbitrary keyboard layout editor layouts, but because it works by stretching and tinting grayscale images there are many limitations on what can be shown, compared to 3D renders. If you're looking for photorealistic visualizations on a limited number of keyboards [kbrenders.com](http://www.kbrenders.com) can be a useful resource. For certain custom work, however you may still have to do post-processing in photoshop, or commission a professional like thesiscamper to create real 3D renders of your set design.

### I've made a great looking set design that I think could be a popular group buy. How do I turn it into a reality?
If you're looking for help with creating a keycap set for a group buy livingspeedbump has a nice [guide](https://www.keychatter.com/2015/10/10/how-to-create-a-keycap-set-for-a-group-buy/) on keychatter.

## Templates
The following templates have their legend sizes and keycap profiles pre-configured for accurate rendering using kle-render. Use them as a starting point for your own designs!

- [SA/DSA on M65 (65%)](http://www.keyboard-layout-editor.com/#/gists/3ca3649e1d048134ddd0e835d1dd735b)
- [GMK on M65](http://www.keyboard-layout-editor.com/#/gists/4319599274157d2a0dd0e38328b76878)
- [SA/DSA on Mech27 (TKL)](http://www.keyboard-layout-editor.com/#/gists/10629d008a99d8d6eb6f8c59414b5dd8)
- [GMK on Mech27](http://www.keyboard-layout-editor.com/#/gists/6e6692825b348f40c040ca9750e469a8)
- [SA/DSA on Mech Mini 2 (40%)](http://www.keyboard-layout-editor.com/#/gists/ea2a231112ffceae047494ac9a93e706)
- [GMK on Mech Mini 2](http://www.keyboard-layout-editor.com/#/gists/eed1f1854dda3999bcdd730f0143c627)
- [SA/DSA on Espectro (96%)](http://www.keyboard-layout-editor.com/#/gists/6b996bea3ebf8a85866ddea606e25de4)
- [GMK on Espectro](http://www.keyboard-layout-editor.com/#/gists/6a03012a82e7bbca14db635142913a7)
- [SA/DSA on Klippe (60%)](http://www.keyboard-layout-editor.com/#/gists/f8369e8d6ae12c6d30bbf6db9731bca5)
- [GMK on Klippe](http://www.keyboard-layout-editor.com/#/gists/c2aedbf20e6a1ee5320a0f89b114d6da)

## Sample Image
![Sample Render](render_output.png)
