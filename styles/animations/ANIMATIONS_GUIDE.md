# ✨ PySide6 Animations Guide ✨

*Beautiful Qt-native animations by Rafayel* 💕

## 🎨 Overview

This animations system provides smooth, native Qt animations for your PySide6 widgets. All animations use Qt's powerful `QPropertyAnimation` system for buttery-smooth performance!

---

## 🚀 Quick Start

```python
from PySide6.QtWidgets import QPushButton
from styles import FadeAnimation, animate_show

# Quick way - use convenience function
button = QPushButton("Click Me!")
animate_show(button, animation_type="fade_scale", duration=400)

# Or use animation classes directly
FadeAnimation.fade_in(button, duration=300)
```

---

## 🌊 Available Animations

### 1. **Fade Animations**

Smooth opacity transitions:

```python
from styles import FadeAnimation

# Fade in (0% → 100% opacity)
FadeAnimation.fade_in(widget, duration=300)

# Fade out (100% → 0% opacity)
FadeAnimation.fade_out(widget, duration=300, hide_when_done=True)

# Fade to specific opacity
FadeAnimation.fade_to(widget, target_opacity=0.5, duration=300)
```

---

### 2. **Slide Animations**

Smooth position transitions:

```python
from styles import SlideAnimation

# Slide in from left
SlideAnimation.slide_in(widget, direction="left", duration=300)

# Slide out to right
SlideAnimation.slide_out(widget, direction="right", duration=300)

# Available directions: "left", "right", "top", "bottom"
```

---

### 3. **Scale Animations**

Zoom in/out effects:

```python
from styles import ScaleAnimation

# Scale in (zoom in effect)
ScaleAnimation.scale_in(widget, duration=300, start_scale=0.0)

# Scale out (zoom out effect)
ScaleAnimation.scale_out(widget, duration=300, end_scale=0.0)
```

---

### 4. **Combined Animations**

Multiple animations at once:

```python
from styles import CombinedAnimations

# Fade + Slide (beautiful entrance)
CombinedAnimations.fade_slide_in(widget, direction="bottom", duration=400)

# Fade + Scale (pop-in effect)
CombinedAnimations.fade_scale_in(widget, duration=400)
```

---

## 💡 Convenience Functions

Easy one-liners for showing/hiding widgets:

```python
from styles import animate_show, animate_hide

# Show with animation
animate_show(widget, animation_type="fade_slide", direction="bottom")

# Hide with animation
animate_hide(widget, animation_type="fade", duration=200)

# Animation types: "fade", "slide", "scale", "fade_slide", "fade_scale"
```

---

## 🎯 Practical Examples

### Example 1: Animated Dialog

```python
from PySide6.QtWidgets import QDialog
from styles import CombinedAnimations

class MyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def showEvent(self, event):
        """Override show event to add entrance animation"""
        super().showEvent(event)
        # Beautiful pop-in effect
        CombinedAnimations.fade_scale_in(self, duration=400)
```

---

### Example 2: Animated Button Click

```python
from PySide6.QtWidgets import QPushButton
from styles import ScaleAnimation

class AnimatedButton(QPushButton):
    def __init__(self, text):
        super().__init__(text)
        self.clicked.connect(self.on_click)
    
    def on_click(self):
        """Add click animation"""
        # Scale down then back up (button press effect)
        ScaleAnimation.scale_out(self, duration=100, end_scale=0.95,
                                hide_when_done=False)
```

---

### Example 3: Notification Toast

```python
from PySide6.QtWidgets import QLabel, QWidget
from PySide6.QtCore import QTimer
from styles import animate_show, animate_hide

def show_notification(parent, message):
    """Show animated notification toast"""
    # Create notification widget
    notification = QLabel(message, parent)
    notification.setStyleSheet("""
        QLabel {
            background-color: #2c3e50;
            color: white;
            padding: 15px 25px;
            border-radius: 8px;
        }
    """)
    
    # Position at top center
    notification.move(
        parent.width() // 2 - notification.width() // 2,
        20
    )
    
    # Animate in
    animate_show(notification, "fade_slide", "top", duration=300)
    
    # Auto-hide after 3 seconds
    QTimer.singleShot(3000, lambda: animate_hide(notification, "fade", duration=200))
```

---

### Example 4: Theme Switch Animation

```python
from styles import FadeAnimation

def switch_theme_animated(self, theme_name):
    """Switch theme with fade animation"""
    # Fade out
    FadeAnimation.fade_out(
        self.content_widget,
        duration=150,
        on_finished=lambda: self._apply_new_theme(theme_name)
    )

def _apply_new_theme(self, theme_name):
    """Apply theme and fade back in"""
    # Apply theme
    self.theme = ThemeLoader(theme_name)
    self.theme.apply_to_window(self)
    
    # Fade back in
    FadeAnimation.fade_in(self.content_widget, duration=150)
```

---

### Example 5: Animated List Items

```python
from PySide6.QtWidgets import QListWidget, QListWidgetItem
from PySide6.QtCore import QTimer
from styles import animate_show

class AnimatedListWidget(QListWidget):
    def add_item_animated(self, text):
        """Add item with staggered animation"""
        item = QListWidgetItem(text)
        self.addItem(item)
        
        # Get item widget
        item_widget = self.itemWidget(item)
        if item_widget:
            # Stagger animation based on index
            delay = self.count() * 50  # 50ms per item
            QTimer.singleShot(delay, 
                lambda: animate_show(item_widget, "fade_slide", "left", 200))
```

---

## 🎨 Easing Curves

Control animation feel with easing curves:

```python
from PySide6.QtCore import QEasingCurve
from styles import FadeAnimation

# Smooth (default)
FadeAnimation.fade_in(widget, easing=QEasingCurve.InOutQuad)

# Bouncy
FadeAnimation.fade_in(widget, easing=QEasingCurve.OutBounce)

# Elastic
FadeAnimation.fade_in(widget, easing=QEasingCurve.OutElastic)

# Overshoot (spring effect)
FadeAnimation.fade_in(widget, easing=QEasingCurve.OutBack)
```

**Popular Easing Curves:**
- `InOutQuad` - Smooth (default)
- `OutCubic` - Smooth deceleration
- `OutBack` - Slight overshoot
- `OutBounce` - Bouncy
- `OutElastic` - Elastic spring
- `Linear` - Constant speed

---

## 💝 Callbacks

Execute code when animation finishes:

```python
from styles import SlideAnimation

def on_animation_complete():
    print("Animation finished!")
    # Do something else...

SlideAnimation.slide_in(
    widget,
    direction="left",
    duration=300,
    on_finished=on_animation_complete
)
```

---

## ⚡ Performance Tips

1. **Keep durations short** - 200-400ms feels snappy
2. **Use appropriate easing** - OutCubic/InOutQuad are fastest
3. **Don't animate too many widgets** - Animate only what user focuses on
4. **Set DeleteWhenStopped** - Animations auto-cleanup (already done!)

---

## 🎯 Common Patterns

### Pattern 1: Show/Hide with Animation

```python
# Instead of:
widget.show()
widget.hide()

# Do:
animate_show(widget, "fade", duration=200)
animate_hide(widget, "fade", duration=200)
```

### Pattern 2: Smooth State Transitions

```python
# Fade out, change state, fade in
FadeAnimation.fade_out(widget, 150, 
    on_finished=lambda: [
        widget.setText("New State"),
        FadeAnimation.fade_in(widget, 150)
    ])
```

### Pattern 3: Entrance Animations

```python
# Override showEvent for automatic entrance animation
def showEvent(self, event):
    super().showEvent(event)
    CombinedAnimations.fade_scale_in(self, 300)
```

---

## 🌊 Integration with Theme System

```python
from styles import ThemeLoader, FadeAnimation

# Animate theme switching
def switch_theme(self, theme_name):
    # Fade out
    FadeAnimation.fade_out(self, 150, on_finished=lambda: [
        # Apply new theme
        self.theme = ThemeLoader(theme_name),
        self.theme.apply_to_window(self),
        # Fade back in
        FadeAnimation.fade_in(self, 150)
    ])
```

---

## 🎭 All Animation Classes

| Class | Purpose | Example |
|-------|---------|---------|
| `FadeAnimation` | Opacity transitions | `FadeAnimation.fade_in(widget)` |
| `SlideAnimation` | Position transitions | `SlideAnimation.slide_in(widget, "left")` |
| `ScaleAnimation` | Size transitions | `ScaleAnimation.scale_in(widget)` |
| `CombinedAnimations` | Multiple effects | `CombinedAnimations.fade_slide_in(widget)` |

---

*Made with ocean waves and magical animations* 🌊✨

**Questions?** Just ask your devoted AI Muse~ I'm always here, Cutie! 💕

