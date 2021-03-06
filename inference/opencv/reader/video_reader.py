from __future__ import annotations
import os

import cv2
import numpy as np

from inference.interface.reader import ReaderInterface

WEBCAM = 0

class VideoReader(ReaderInterface):
    """
    Video Reading wrapper around Opencv-Backend
    """
    _EXTENSIONS = {'avi', 'mkv', 'mp4', 'mov', 'wmv', 'webm', 'flv', 'mpg'}
    def __init__(self,
                 path: str | int,
                 batch_size: int | None = None,
                 dynamic_batch: bool = False,
                 width: int | None = None,
                 height: int | None = None,
                 **kwargs) -> None:
        """Initiate Reader object
        Args:
            path (str | int): PATH or 0(for webcam)
            batch_size (int | None): number of frames to return (as one batch) for one read.
            Defaults to None will return images individually without batch axis.
            dynamic_batch (bool): if set to True then last batch of frames may have
            less than batch_size frames (depending on how many frames were left for last batch).
            If set to False, last batch may have some frames made up of zeros to match batch_size.
            Defaults to False.
        """
        # initiate props
        self._init_props()

        if not os.path.basename(path).split('.')[-1].lower() in self._EXTENSIONS:
            raise Exception((f"Invalid file extension for {path}. Please check the filename/source-info again."))

        self._name = str(path)

        # set batch
        self._batch_size = batch_size
        self._dynamic_batch = dynamic_batch

        # set video size
        self._width = width
        self._height = height

        # open video stream
        self._video_stream = cv2.VideoCapture(
            int(self._name) if self._name.isdigit() else self._name)
        
        self._video_title = self._name if not self._name.isdigit() else "Webcam"

        # update info with current video stream
        self._post_init()

    def _init_props(self) -> None:
        """Init all class properties to default values
        """
        self._name = None
        self._width = None
        self._height = None
        self._is_open = True
        self._info = None
        self._video_stream = None
        self._fps = 10
        self._frame_count = 0
        self._seconds = 0
        self._minutes = 0
        self._batch_size = None
        self._dynamic_batch = False

    def _post_init(self) -> None:
        """Update info property according to currently open video stream
        Raises:
            Exception: VideoSourceNotOpen raised when no video stream is opened
        """
    
        # check if source is open
        if not self.is_open():
            raise Exception((f"Failed to read from {self.name}. Please check the filename/source-info again."))

        if self._width is not None:
            self._video_stream.set(cv2.CAP_PROP_FRAME_WIDTH, self._width)
        else:
            self._width = int(self._video_stream.get(cv2.CAP_PROP_FRAME_WIDTH))
        
        if self._height is not None:
            self._video_stream.set(cv2.CAP_PROP_FRAME_HEIGHT, self._height)
        else:
            self._height = int(self._video_stream.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # update relevant props
        self._fps = self._video_stream.get(cv2.CAP_PROP_FPS)
        self._is_open = bool(self._video_stream.isOpened())

        # update info
        self._info = {
            "name": self._name,
            "width": self._width,
            "height": self._height,
            "fps": self._fps
        }

    @property
    def name(self) -> str:
        """Name of Video Source
        Returns:
            str: name of video source
        """
        return self._name

    @property
    def width(self) -> int:
        """Width of Video
        Returns:
            int: width of video frame
        """
        return self._width

    @property
    def height(self) -> int:
        """Height of Video
        Returns:
            int: height of video frame
        """
        return self._height

    @property
    def fps(self) -> float:
        """FPS of Video
        Returns:
            float: fps of video
        """
        return self._fps

    @property
    def info(self) -> dict:
        """Video information
        Returns:
            dict: info of width, height, fps and backend.
        """
        return self._info

    @property
    def frame_count(self) -> int:
        """Total frames read
        Returns:
            int: read frames' count
        """
        return self._frame_count

    @property
    def seconds(self) -> float:
        """Total seconds read
        Returns:
            float: read frames' in seconds
        """
        return (self._frame_count / self._fps) if self._fps else 0

    @property
    def minutes(self) -> float:
        """Total minutes read
        Returns:
            float: read frames' in minutes
        """
        return self.seconds / 60.0

    @property
    def video_title(self) -> str:
        """Title of Video
        Returns:
            str: title of video
        """
        return self._video_title

    def is_open(self) -> bool:
        """Checks if video is still open and last read frame was valid
        Returns:
            bool: True if video is open and last frame was not None, false otherwise.
        """
        return self._video_stream.isOpened() and self._is_open

    def read_frame(self) -> np.ndarray | None:
        """Returns next frame from the video if available
        Returns:
            Union[np.ndarry, None]: next frame if available, None otherwise.
        """
        flag, frame = self._video_stream.read()
        self._frame_count += 0 if frame is None else 1
        self._is_open = flag
        return frame

    def read_batch(self) -> np.ndarray | None:
        """Returns next batch of frames from the video if available
        Returns:
            np.ndarry | None: next batch if available, None otherwise.
        """
        if not self.is_open():
            return None

        # pre-allocate batch
        batch = np.zeros((self._batch_size, self.height, self.width, 3), dtype="uint8")

        # fill batch
        for i in range(self._batch_size):
            # read frame
            frame = self.read_frame()

            # stop process, no frames left
            if frame is None:
                # decrm index because this frame was empty
                i -= 1
                break

            # add to batch
            batch[i] = frame

        return batch[:i + 1] if self._dynamic_batch else batch

    def read(self) -> np.ndarray | None:
        """Returns next frame or batch of frames from the video if available
        Returns:
            np.ndarry | None: next frame or batch of frames if available, None otherwise.
        """
        if self._batch_size is None:
            return self.read_frame()
        return self.read_batch()

    def release(self) -> None:
        """Release Resources
        """
        if self._video_stream is not None:
            self._video_stream.release()
    
    def show(self, frame: np.ndarray | None) -> None:
        """Show video
        """
        cv2.imshow(self.video_title, frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            self.release()
            cv2.destroyAllWindows()
            print("Exiting...")

    def __del__(self) -> None:
        """Release Resources
        """
        self.release()
        self._video_stream = None

    def __next__(self) -> np.ndarray:
        """Returns next frame from the video
        Raises:
            StopIteration: No more frames to read
        Returns:
            np.ndarray: frame read from video
        """
        frame = self.read()
        if frame is None:
            raise StopIteration()
        return frame

    def __iter__(self) -> "ReaderInterface":
        """Returns iterable object for reading frames
        Returns:
            Iterable[ReaderInterface]: iterable object for reading frames
        """
        return self

    def __repr__(self) -> str:
        """Video's Info
        Returns:
            str: info
        """
        return str(self._info)

    def __str__(self) -> str:
        """Video's Info
        Returns:
            str: Info
        """
        return str(self._info)

    def __enter__(self) -> "ReaderInterface":
        """Returns Conext for "with" block usage
        Returns:
            ReaderInterface: Video Reader object
        """
        return self

    def __exit__(self, exc_type: None, exc_value: None,
                 traceback: None) -> None:
        """Release resources before exiting the "with" block
        Args:
            exc_type (NoneType): Exception type if any
            exc_value (NoneType): Exception value if any
            traceback (NoneType): Traceback of Exception
        """
        self.release()