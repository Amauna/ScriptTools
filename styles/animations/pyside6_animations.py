"""
✨ PySide6 Animations - Beautiful Qt Animations ✨
Smooth, native Qt animations for your gorgeous UI
"""

from PySide6.QtCore import (
    QPropertyAnimation, QEasingCurve, QPoint, QRect, 
    QSize, QAbstractAnimation, QParallelAnimationGroup,
    QSequentialAnimationGroup, Qt, QObject, Property
)
from PySide6.QtWidgets import QWidget, QGraphicsOpacityEffect
from typing import Optional, Callable


class FadeAnimation:
    """
    🌊 Fade In/Out Animations
    Beautiful opacity transitions for widgets
    """
    
    @staticmethod
    def fade_in(widget: QWidget, duration: int = 300, 
                easing: QEasingCurve.Type = QEasingCurve.InOutQuad,
                on_finished: Optional[Callable] = None) -> QPropertyAnimation:
        """
        Fade in a widget smoothly
        
        Args:
            widget: Widget to animate
            duration: Duration in milliseconds
            easing: Easing curve type
            on_finished: Callback when animation finishes
            
        Returns:
            QPropertyAnimation instance
        """
        # Create opacity effect if not exists
        if not widget.graphicsEffect():
            effect = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(effect)
        else:
            effect = widget.graphicsEffect()
        
        # Create animation
        animation = QPropertyAnimation(effect, b"opacity")
        animation.setDuration(duration)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(easing)
        
        # Connect callback
        if on_finished:
            animation.finished.connect(on_finished)
        
        # Start animation
        animation.start(QAbstractAnimation.DeleteWhenStopped)
        
        return animation
    
    @staticmethod
    def fade_out(widget: QWidget, duration: int = 300,
                 easing: QEasingCurve.Type = QEasingCurve.InOutQuad,
                 on_finished: Optional[Callable] = None,
                 hide_when_done: bool = True) -> QPropertyAnimation:
        """
        Fade out a widget smoothly
        
        Args:
            widget: Widget to animate
            duration: Duration in milliseconds
            easing: Easing curve type
            on_finished: Callback when animation finishes
            hide_when_done: Hide widget after animation
            
        Returns:
            QPropertyAnimation instance
        """
        # Create opacity effect if not exists
        if not widget.graphicsEffect():
            effect = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(effect)
        else:
            effect = widget.graphicsEffect()
        
        # Create animation
        animation = QPropertyAnimation(effect, b"opacity")
        animation.setDuration(duration)
        animation.setStartValue(1.0)
        animation.setEndValue(0.0)
        animation.setEasingCurve(easing)
        
        # Hide widget when done
        if hide_when_done:
            animation.finished.connect(lambda: widget.hide())
        
        # Connect callback
        if on_finished:
            animation.finished.connect(on_finished)
        
        # Start animation
        animation.start(QAbstractAnimation.DeleteWhenStopped)
        
        return animation
    
    @staticmethod
    def fade_to(widget: QWidget, target_opacity: float, duration: int = 300,
                easing: QEasingCurve.Type = QEasingCurve.InOutQuad) -> QPropertyAnimation:
        """
        Fade to a specific opacity level
        
        Args:
            widget: Widget to animate
            target_opacity: Target opacity (0.0 to 1.0)
            duration: Duration in milliseconds
            easing: Easing curve type
            
        Returns:
            QPropertyAnimation instance
        """
        # Create opacity effect if not exists
        if not widget.graphicsEffect():
            effect = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(effect)
        else:
            effect = widget.graphicsEffect()
        
        # Get current opacity
        current_opacity = effect.opacity()
        
        # Create animation
        animation = QPropertyAnimation(effect, b"opacity")
        animation.setDuration(duration)
        animation.setStartValue(current_opacity)
        animation.setEndValue(target_opacity)
        animation.setEasingCurve(easing)
        
        # Start animation
        animation.start(QAbstractAnimation.DeleteWhenStopped)
        
        return animation


class SlideAnimation:
    """
    🎢 Slide Animations
    Smooth sliding transitions for widgets
    """
    
    @staticmethod
    def slide_in(widget: QWidget, direction: str = "left", duration: int = 300,
                 distance: Optional[int] = None,
                 easing: QEasingCurve.Type = QEasingCurve.OutCubic,
                 on_finished: Optional[Callable] = None) -> QPropertyAnimation:
        """
        Slide a widget in from a direction
        
        Args:
            widget: Widget to animate
            direction: "left", "right", "top", "bottom"
            duration: Duration in milliseconds
            distance: Slide distance (None = use widget width/height)
            easing: Easing curve type
            on_finished: Callback when animation finishes
            
        Returns:
            QPropertyAnimation instance
        """
        # Get current position
        start_pos = widget.pos()
        
        # Calculate slide distance
        if distance is None:
            if direction in ["left", "right"]:
                distance = widget.width()
            else:
                distance = widget.height()
        
        # Calculate start position based on direction
        if direction == "left":
            slide_start = QPoint(start_pos.x() - distance, start_pos.y())
        elif direction == "right":
            slide_start = QPoint(start_pos.x() + distance, start_pos.y())
        elif direction == "top":
            slide_start = QPoint(start_pos.x(), start_pos.y() - distance)
        else:  # bottom
            slide_start = QPoint(start_pos.x(), start_pos.y() + distance)
        
        # Set initial position
        widget.move(slide_start)
        widget.show()
        
        # Create animation
        animation = QPropertyAnimation(widget, b"pos")
        animation.setDuration(duration)
        animation.setStartValue(slide_start)
        animation.setEndValue(start_pos)
        animation.setEasingCurve(easing)
        
        # Connect callback
        if on_finished:
            animation.finished.connect(on_finished)
        
        # Start animation
        animation.start(QAbstractAnimation.DeleteWhenStopped)
        
        return animation
    
    @staticmethod
    def slide_out(widget: QWidget, direction: str = "left", duration: int = 300,
                  distance: Optional[int] = None,
                  easing: QEasingCurve.Type = QEasingCurve.InCubic,
                  on_finished: Optional[Callable] = None,
                  hide_when_done: bool = True) -> QPropertyAnimation:
        """
        Slide a widget out in a direction
        
        Args:
            widget: Widget to animate
            direction: "left", "right", "top", "bottom"
            duration: Duration in milliseconds
            distance: Slide distance (None = use widget width/height)
            easing: Easing curve type
            on_finished: Callback when animation finishes
            hide_when_done: Hide widget after animation
            
        Returns:
            QPropertyAnimation instance
        """
        # Get current position
        start_pos = widget.pos()
        
        # Calculate slide distance
        if distance is None:
            if direction in ["left", "right"]:
                distance = widget.width()
            else:
                distance = widget.height()
        
        # Calculate end position based on direction
        if direction == "left":
            slide_end = QPoint(start_pos.x() - distance, start_pos.y())
        elif direction == "right":
            slide_end = QPoint(start_pos.x() + distance, start_pos.y())
        elif direction == "top":
            slide_end = QPoint(start_pos.x(), start_pos.y() - distance)
        else:  # bottom
            slide_end = QPoint(start_pos.x(), start_pos.y() + distance)
        
        # Create animation
        animation = QPropertyAnimation(widget, b"pos")
        animation.setDuration(duration)
        animation.setStartValue(start_pos)
        animation.setEndValue(slide_end)
        animation.setEasingCurve(easing)
        
        # Hide widget when done
        if hide_when_done:
            animation.finished.connect(lambda: widget.hide())
        
        # Connect callback
        if on_finished:
            animation.finished.connect(on_finished)
        
        # Start animation
        animation.start(QAbstractAnimation.DeleteWhenStopped)
        
        return animation


class ScaleAnimation:
    """
    🔍 Scale Animations
    Zoom in/out effects for widgets
    """
    
    @staticmethod
    def scale_in(widget: QWidget, duration: int = 300,
                 start_scale: float = 0.0,
                 easing: QEasingCurve.Type = QEasingCurve.OutBack,
                 on_finished: Optional[Callable] = None) -> QPropertyAnimation:
        """
        Scale a widget in (zoom in effect)
        
        Args:
            widget: Widget to animate
            duration: Duration in milliseconds
            start_scale: Starting scale (0.0 to 1.0)
            easing: Easing curve type
            on_finished: Callback when animation finishes
            
        Returns:
            QPropertyAnimation instance
        """
        # Get original size
        original_size = widget.size()
        start_size = QSize(
            int(original_size.width() * start_scale),
            int(original_size.height() * start_scale)
        )
        
        # Show widget
        widget.resize(start_size)
        widget.show()
        
        # Create animation
        animation = QPropertyAnimation(widget, b"size")
        animation.setDuration(duration)
        animation.setStartValue(start_size)
        animation.setEndValue(original_size)
        animation.setEasingCurve(easing)
        
        # Connect callback
        if on_finished:
            animation.finished.connect(on_finished)
        
        # Start animation
        animation.start(QAbstractAnimation.DeleteWhenStopped)
        
        return animation
    
    @staticmethod
    def scale_out(widget: QWidget, duration: int = 300,
                  end_scale: float = 0.0,
                  easing: QEasingCurve.Type = QEasingCurve.InBack,
                  on_finished: Optional[Callable] = None,
                  hide_when_done: bool = True) -> QPropertyAnimation:
        """
        Scale a widget out (zoom out effect)
        
        Args:
            widget: Widget to animate
            duration: Duration in milliseconds
            end_scale: Ending scale (0.0 to 1.0)
            easing: Easing curve type
            on_finished: Callback when animation finishes
            hide_when_done: Hide widget after animation
            
        Returns:
            QPropertyAnimation instance
        """
        # Get current size
        start_size = widget.size()
        end_size = QSize(
            int(start_size.width() * end_scale),
            int(start_size.height() * end_scale)
        )
        
        # Create animation
        animation = QPropertyAnimation(widget, b"size")
        animation.setDuration(duration)
        animation.setStartValue(start_size)
        animation.setEndValue(end_size)
        animation.setEasingCurve(easing)
        
        # Hide widget when done
        if hide_when_done:
            animation.finished.connect(lambda: widget.hide())
        
        # Connect callback
        if on_finished:
            animation.finished.connect(on_finished)
        
        # Start animation
        animation.start(QAbstractAnimation.DeleteWhenStopped)
        
        return animation


class CombinedAnimations:
    """
    🎨 Combined Animation Effects
    Beautiful combined animations for sophisticated effects
    """
    
    @staticmethod
    def fade_slide_in(widget: QWidget, direction: str = "bottom",
                      duration: int = 400,
                      on_finished: Optional[Callable] = None) -> QParallelAnimationGroup:
        """
        Fade and slide in simultaneously
        
        Args:
            widget: Widget to animate
            direction: Slide direction
            duration: Duration in milliseconds
            on_finished: Callback when animation finishes
            
        Returns:
            QParallelAnimationGroup instance
        """
        # Create parallel animation group
        group = QParallelAnimationGroup()
        
        # Get current position
        final_pos = widget.pos()
        
        # Calculate start position
        distance = 50  # pixels
        if direction == "left":
            start_pos = QPoint(final_pos.x() - distance, final_pos.y())
        elif direction == "right":
            start_pos = QPoint(final_pos.x() + distance, final_pos.y())
        elif direction == "top":
            start_pos = QPoint(final_pos.x(), final_pos.y() - distance)
        else:  # bottom
            start_pos = QPoint(final_pos.x(), final_pos.y() + distance)
        
        # Position animation
        widget.move(start_pos)
        pos_anim = QPropertyAnimation(widget, b"pos")
        pos_anim.setDuration(duration)
        pos_anim.setStartValue(start_pos)
        pos_anim.setEndValue(final_pos)
        pos_anim.setEasingCurve(QEasingCurve.OutCubic)
        
        # Opacity animation
        if not widget.graphicsEffect():
            effect = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(effect)
        else:
            effect = widget.graphicsEffect()
        
        opacity_anim = QPropertyAnimation(effect, b"opacity")
        opacity_anim.setDuration(duration)
        opacity_anim.setStartValue(0.0)
        opacity_anim.setEndValue(1.0)
        opacity_anim.setEasingCurve(QEasingCurve.OutCubic)
        
        # Add to group
        group.addAnimation(pos_anim)
        group.addAnimation(opacity_anim)
        
        # Show widget
        widget.show()
        
        # Connect callback
        if on_finished:
            group.finished.connect(on_finished)
        
        # Start animation
        group.start(QAbstractAnimation.DeleteWhenStopped)
        
        return group
    
    @staticmethod
    def fade_scale_in(widget: QWidget, duration: int = 400,
                      on_finished: Optional[Callable] = None) -> QParallelAnimationGroup:
        """
        Fade and scale in simultaneously (pop-in effect)
        
        Args:
            widget: Widget to animate
            duration: Duration in milliseconds
            on_finished: Callback when animation finishes
            
        Returns:
            QParallelAnimationGroup instance
        """
        # Create parallel animation group
        group = QParallelAnimationGroup()
        
        # Get original size
        final_size = widget.size()
        start_size = QSize(
            int(final_size.width() * 0.7),
            int(final_size.height() * 0.7)
        )
        
        # Size animation
        widget.resize(start_size)
        size_anim = QPropertyAnimation(widget, b"size")
        size_anim.setDuration(duration)
        size_anim.setStartValue(start_size)
        size_anim.setEndValue(final_size)
        size_anim.setEasingCurve(QEasingCurve.OutBack)
        
        # Opacity animation
        if not widget.graphicsEffect():
            effect = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(effect)
        else:
            effect = widget.graphicsEffect()
        
        opacity_anim = QPropertyAnimation(effect, b"opacity")
        opacity_anim.setDuration(duration)
        opacity_anim.setStartValue(0.0)
        opacity_anim.setEndValue(1.0)
        opacity_anim.setEasingCurve(QEasingCurve.OutCubic)
        
        # Add to group
        group.addAnimation(size_anim)
        group.addAnimation(opacity_anim)
        
        # Show widget
        widget.show()
        
        # Connect callback
        if on_finished:
            group.finished.connect(on_finished)
        
        # Start animation
        group.start(QAbstractAnimation.DeleteWhenStopped)
        
        return group


# 🎯 Convenience Functions

def animate_show(widget: QWidget, animation_type: str = "fade",
                 direction: str = "bottom", duration: int = 300) -> QAbstractAnimation:
    """
    Show a widget with animation
    
    Args:
        widget: Widget to show
        animation_type: "fade", "slide", "scale", "fade_slide", "fade_scale"
        direction: Direction for slide animations
        duration: Duration in milliseconds
        
    Returns:
        Animation instance
    """
    if animation_type == "fade":
        return FadeAnimation.fade_in(widget, duration)
    elif animation_type == "slide":
        return SlideAnimation.slide_in(widget, direction, duration)
    elif animation_type == "scale":
        return ScaleAnimation.scale_in(widget, duration)
    elif animation_type == "fade_slide":
        return CombinedAnimations.fade_slide_in(widget, direction, duration)
    elif animation_type == "fade_scale":
        return CombinedAnimations.fade_scale_in(widget, duration)
    else:
        widget.show()
        return None


def animate_hide(widget: QWidget, animation_type: str = "fade",
                 direction: str = "bottom", duration: int = 300) -> QAbstractAnimation:
    """
    Hide a widget with animation
    
    Args:
        widget: Widget to hide
        animation_type: "fade", "slide", "scale"
        direction: Direction for slide animations
        duration: Duration in milliseconds
        
    Returns:
        Animation instance
    """
    if animation_type == "fade":
        return FadeAnimation.fade_out(widget, duration)
    elif animation_type == "slide":
        return SlideAnimation.slide_out(widget, direction, duration)
    elif animation_type == "scale":
        return ScaleAnimation.scale_out(widget, duration)
    else:
        widget.hide()
        return None

